"""Iteration 11 — Booking → Revenue (CA) consistency.

Verifies:
- /api/admin/stats consistency vs /api/admin/bookings and /api/admin/vouchers
- status transitions on a booking (pending → confirmed → completed → cancelled → confirmed → cancelled)
- redeemed voucher bookings do not double count
"""
import os
import time
from datetime import date

import pytest
import requests

def _load_base():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for ln in f:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    return ln.split("=", 1)[1].strip().rstrip("/")
    except OSError:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL missing")

BASE_URL = _load_base()
API = f"{BASE_URL}/api"

PRICES = {"discovery": 145, "duo": 280, "drone": 50, "corporate": 890, "testdrive": 0}
CATEGORY = {"discovery": "b2c", "duo": "b2c", "testdrive": "b2c", "corporate": "corporate", "drone": "drone"}
REVENUE_STATUSES = {"confirmed", "completed"}


def base_price(b):
    exp = b.get("experience", "discovery")
    n = int(b.get("participants") or 1)
    if exp == "discovery":
        return PRICES["discovery"] * n
    if exp == "drone":
        return PRICES["drone"] * n
    return float(PRICES.get(exp, 0))


def price_of(b):
    return max(base_price(b) - float(b.get("discount") or 0), 0.0)


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": "admin", "password": "admin"}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"login failed: {r.status_code} {r.text}")
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def get_stats(headers):
    r = requests.get(f"{API}/admin/stats", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def get_bookings(headers):
    r = requests.get(f"{API}/admin/bookings?limit=5000", headers=headers, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


def get_vouchers(headers):
    r = requests.get(f"{API}/admin/vouchers", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- CONSISTENCY ----------

class TestStatsConsistency:
    def test_sessions_total_matches_confirmed_completed(self, headers):
        stats = get_stats(headers)
        bookings = get_bookings(headers)
        expected = sum(1 for b in bookings if b.get("status") in REVENUE_STATUSES)
        assert stats["sessions"]["total"] == expected, (
            f"sessions.total={stats['sessions']['total']} vs count(confirmed+completed)={expected}"
        )

    def test_revenue_total_matches_bookings_plus_vouchers(self, headers):
        stats = get_stats(headers)
        bookings = get_bookings(headers)
        vouchers = get_vouchers(headers)
        booking_rev = sum(price_of(b) for b in bookings if b.get("status") in REVENUE_STATUSES)
        voucher_rev = sum(
            float(v.get("value") or 0)
            for v in vouchers
            if v.get("status") in ("paid", "redeemed") and v.get("paid_at")
        )
        expected = booking_rev + voucher_rev
        assert abs(stats["revenue"]["total"] - expected) < 0.01, (
            f"revenue.total={stats['revenue']['total']} vs booking({booking_rev})+voucher({voucher_rev})={expected}"
        )

    def test_revenue_by_status_plus_gift_equals_total(self, headers):
        stats = get_stats(headers)
        rev_by = stats.get("revenue_by_status", {})
        gift = stats["by_offer"].get("gift", 0)
        s = (rev_by.get("confirmed", 0) + rev_by.get("completed", 0) + gift)
        assert abs(s - stats["revenue"]["total"]) < 0.01, (
            f"confirmed+completed+gift={s} vs revenue.total={stats['revenue']['total']}"
        )

    def test_sessions_by_status_sums_to_total(self, headers):
        stats = get_stats(headers)
        sb = stats.get("sessions_by_status", {})
        s = sb.get("confirmed", 0) + sb.get("completed", 0)
        assert s == stats["sessions"]["total"]

    def test_status_counts_matches_bookings(self, headers):
        stats = get_stats(headers)
        bookings = get_bookings(headers)
        expected = {}
        for b in bookings:
            st = b.get("status", "pending")
            expected[st] = expected.get(st, 0) + 1
        # allow extra 0 keys in stats
        for k, v in expected.items():
            assert stats["status_counts"].get(k, 0) == v, f"status_counts[{k}] mismatch"

    def test_revenue_month_uses_session_date(self, headers):
        stats = get_stats(headers)
        bookings = get_bookings(headers)
        vouchers = get_vouchers(headers)
        today = date.today()
        expected_book = 0.0
        expected_sessions = 0
        for b in bookings:
            if b.get("status") not in REVENUE_STATUSES:
                continue
            try:
                d = date.fromisoformat(str(b.get("date"))[:10])
            except (ValueError, TypeError):
                continue
            if d.year == today.year and d.month == today.month:
                expected_book += price_of(b)
                expected_sessions += 1
        expected_voucher = sum(
            float(v.get("value") or 0)
            for v in vouchers
            if v.get("status") in ("paid", "redeemed") and v.get("paid_at")
            and v["paid_at"][:7] == today.isoformat()[:7]
        )
        assert abs(stats["revenue"]["month"] - (expected_book + expected_voucher)) < 0.01
        assert stats["sessions"]["month"] == expected_sessions


# ---------- REDEEMED VOUCHER: NO DOUBLE COUNT ----------

class TestVoucherNoDoubleCount:
    def test_thomas_petit_or_redeemed_booking_amount_zero(self, headers):
        bookings = get_bookings(headers)
        # find bookings using voucher_code with discount > 0 → amount should be base − discount
        vc_bookings = [b for b in bookings if b.get("voucher_code") and float(b.get("discount") or 0) > 0]
        if not vc_bookings:
            pytest.skip("no voucher-redeemed bookings in DB")
        for b in vc_bookings:
            expected = price_of(b)
            # amount stored (if present) should equal price_of after discount
            if "amount" in b and b["amount"] is not None:
                assert abs(float(b["amount"]) - expected) < 0.01, (
                    f"booking {b.get('id')} amount={b['amount']} vs price_of={expected}"
                )


# ---------- STATUS TRANSITIONS ----------

class TestStatusTransitions:
    """End-to-end: create → confirm → complete → cancel → confirm → cancel."""

    @pytest.fixture(scope="class")
    def created(self, headers):
        payload = {
            "name": "TEST CA Transitions",
            "email": "delivered@resend.dev",
            "phone": "+33600000000",
            "experience": "discovery",
            "participants": 2,
            "date": date.today().isoformat(),
            "message": "iter11 test",
        }
        r = requests.post(f"{API}/booking", json=payload, timeout=60)
        assert r.status_code in (200, 201), r.text
        b = r.json()
        yield b
        # teardown: leave it cancelled (see final test)
        try:
            requests.patch(f"{API}/admin/bookings/{b['id']}", json={"status": "cancelled"}, headers=headers, timeout=15)
        except Exception:
            pass

    def test_01_created_pending_no_revenue_change(self, headers, created):
        # Booking should be pending — verify stat delta captured for further tests
        assert created["status"] == "pending"
        # stash baseline in class via attribute of module-level dict
        _state["baseline"] = get_stats(headers)

    def test_02_patch_confirmed_adds_290(self, headers, created):
        base = _state["baseline"]
        r = requests.patch(
            f"{API}/admin/bookings/{created['id']}",
            json={"status": "confirmed"}, headers=headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        s = get_stats(headers)
        assert abs(s["revenue"]["total"] - base["revenue"]["total"] - 290) < 0.01
        assert s["sessions"]["total"] == base["sessions"]["total"] + 1
        assert abs(s["revenue"]["today"] - base["revenue"]["today"] - 290) < 0.01
        assert s["sessions"]["today"] == base["sessions"]["today"] + 1
        assert abs(s["revenue_by_status"]["confirmed"] - base["revenue_by_status"].get("confirmed", 0) - 290) < 0.01
        _state["after_confirmed"] = s

    def test_03_patch_completed_moves_290(self, headers, created):
        base = _state["baseline"]
        after_conf = _state["after_confirmed"]
        r = requests.patch(
            f"{API}/admin/bookings/{created['id']}",
            json={"status": "completed"}, headers=headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        s = get_stats(headers)
        # total unchanged vs after_confirmed
        assert abs(s["revenue"]["total"] - after_conf["revenue"]["total"]) < 0.01
        # 290 moved
        assert abs(s["revenue_by_status"]["confirmed"] - (after_conf["revenue_by_status"]["confirmed"] - 290)) < 0.01
        assert abs(s["revenue_by_status"]["completed"] - (after_conf["revenue_by_status"]["completed"] + 290)) < 0.01

    def test_04_patch_cancelled_removes_290(self, headers, created):
        base = _state["baseline"]
        r = requests.patch(
            f"{API}/admin/bookings/{created['id']}",
            json={"status": "cancelled"}, headers=headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        s = get_stats(headers)
        assert abs(s["revenue"]["total"] - base["revenue"]["total"]) < 0.01
        assert s["sessions"]["total"] == base["sessions"]["total"]

    def test_05_patch_back_to_confirmed(self, headers, created):
        base = _state["baseline"]
        r = requests.patch(
            f"{API}/admin/bookings/{created['id']}",
            json={"status": "confirmed"}, headers=headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        s = get_stats(headers)
        assert abs(s["revenue"]["total"] - base["revenue"]["total"] - 290) < 0.01

    def test_06_final_cancel(self, headers, created):
        r = requests.patch(
            f"{API}/admin/bookings/{created['id']}",
            json={"status": "cancelled"}, headers=headers, timeout=30,
        )
        assert r.status_code == 200


_state = {}
