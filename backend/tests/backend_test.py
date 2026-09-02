"""Backend tests for Canary Foil Club — auth, bookings, admin stats."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://canary-foil-club.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@canaryfoilclub.com"
ADMIN_PASSWORD = "Foil!Club2026"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and data["email"] == ADMIN_EMAIL and data["role"] == "admin"
    return data["token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- Auth ---
class TestAuth:
    def test_login_success(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert d["role"] == "admin"
        assert isinstance(d["token"], str) and len(d["token"]) > 20

    def test_login_wrong_password(self):
        # Use a distinct email to avoid locking admin
        r = requests.post(f"{API}/auth/login", json={"email": "nobody@test.com", "password": "wrong"}, timeout=15)
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_login_lockout_after_5(self):
        email = f"lock-{uuid.uuid4().hex[:6]}@test.com"
        last = None
        for _ in range(5):
            last = requests.post(f"{API}/auth/login", json={"email": email, "password": "bad"}, timeout=15)
            assert last.status_code == 401
        # 6th attempt should be 429
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "bad"}, timeout=15)
        assert r.status_code == 429, f"expected 429 after lockout, got {r.status_code}"

    def test_me_without_token(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_me_with_token(self, auth_headers):
        r = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert d["role"] == "admin"
        assert "password_hash" not in d


# --- Bookings list ---
class TestBookings:
    def test_bookings_no_token(self):
        r = requests.get(f"{API}/bookings", timeout=15)
        assert r.status_code == 401

    def test_bookings_with_token(self, auth_headers):
        r = requests.get(f"{API}/bookings", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
            # sorted desc by created_at
            first = data[0]
            assert "amount" in first
            assert "partner" in first
            # check sorting on first 5
            times = [b["created_at"] for b in data[:5]]
            assert times == sorted(times, reverse=True)


# --- Public booking ---
class TestPublicBooking:
    def test_create_with_partner(self):
        payload = {
            "name": "TEST User",
            "email": "delivered@resend.dev",
            "phone": "+34600000000",
            "experience": "discovery",
            "date": "2026-06-15",
            "participants": 2,
            "partner": True,
            "partner_name": "TEST Hotel",
            "lang": "fr",
        }
        r = requests.post(f"{API}/booking", json=payload, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["partner"] is True
        assert d["partner_name"] == "TEST Hotel"
        assert d["amount"] == 290  # 145 * 2
        assert d["status"] == "pending"


# --- Admin stats ---
class TestStats:
    def test_stats_shape_and_math(self, auth_headers):
        # Get all bookings and stats
        rb = requests.get(f"{API}/bookings", headers=auth_headers, timeout=15)
        assert rb.status_code == 200
        bookings = rb.json()

        rs = requests.get(f"{API}/admin/stats", headers=auth_headers, timeout=15)
        assert rs.status_code == 200
        s = rs.json()
        # shape
        for k in ["revenue", "sessions", "occupancy", "by_offer", "commissions", "commission_rate", "pending", "total_bookings", "recent"]:
            assert k in s, f"missing {k}"
        assert s["commission_rate"] == 0.20
        assert s["occupancy"]["boards"] == 3
        assert s["occupancy"]["slots_per_day"] == 4
        for k in ["b2c", "corporate", "drone"]:
            assert k in s["by_offer"]
        assert len(s["recent"]) <= 10
        assert s["total_bookings"] == len(bookings)

        # Math check
        revenue_statuses = {"confirmed", "completed"}
        expected_total = 0.0
        expected_comm = 0.0
        expected_by = {"b2c": 0.0, "corporate": 0.0, "drone": 0.0}
        cat = {"discovery": "b2c", "duo": "b2c", "testdrive": "b2c", "corporate": "corporate", "drone": "drone"}
        for b in bookings:
            if b.get("status") not in revenue_statuses:
                continue
            amt = b["amount"]
            expected_total += amt
            expected_by[cat.get(b.get("experience"), "b2c")] += amt
            if b.get("partner"):
                expected_comm += amt * 0.20
        assert abs(s["revenue"]["total"] - expected_total) < 0.01
        assert abs(s["commissions"] - round(expected_comm, 2)) < 0.01
        for k in expected_by:
            assert abs(s["by_offer"][k] - expected_by[k]) < 0.01


# --- Admin patch booking ---
class TestPatchBooking:
    def test_patch_flows(self, auth_headers):
        # find a booking to test on
        r = requests.get(f"{API}/bookings", headers=auth_headers, timeout=15)
        bookings = r.json()
        assert bookings, "need at least one booking (seeded)"
        target = bookings[0]
        bid = target["id"]
        orig_status = target["status"]
        orig_partner = target.get("partner", False)

        # no token
        r = requests.patch(f"{API}/admin/bookings/{bid}", json={"status": "confirmed"}, timeout=15)
        assert r.status_code == 401

        # unknown id
        r = requests.patch(f"{API}/admin/bookings/does-not-exist-123", json={"status": "confirmed"}, headers=auth_headers, timeout=15)
        assert r.status_code == 404

        # invalid status
        r = requests.patch(f"{API}/admin/bookings/{bid}", json={"status": "banana"}, headers=auth_headers, timeout=15)
        assert r.status_code == 400

        # empty body
        r = requests.patch(f"{API}/admin/bookings/{bid}", json={}, headers=auth_headers, timeout=15)
        assert r.status_code == 400

        # valid status update
        r = requests.patch(f"{API}/admin/bookings/{bid}", json={"status": "confirmed"}, headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

        # toggle partner
        r = requests.patch(f"{API}/admin/bookings/{bid}", json={"partner": not orig_partner}, headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["partner"] == (not orig_partner)

        # restore
        requests.patch(f"{API}/admin/bookings/{bid}", json={"status": orig_status}, headers=auth_headers, timeout=15)
        requests.patch(f"{API}/admin/bookings/{bid}", json={"partner": orig_partner}, headers=auth_headers, timeout=15)
