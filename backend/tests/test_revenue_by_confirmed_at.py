"""Test revenue.today/month use confirmed_at cash_date instead of session date."""
import os
import requests
import pytest
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://canary-foil-club.preview.emergentagent.com').rstrip('/')
BOOKING_ID = "cffc7ed6-90ad-4c33-be84-d8ced5382812"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin", "password": "admin"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}"}


def get_stats(h):
    r = requests.get(f"{BASE_URL}/api/admin/stats", headers=h)
    assert r.status_code == 200
    return r.json()


def get_booking(h, bid):
    r = requests.get(f"{BASE_URL}/api/bookings", headers=h)
    assert r.status_code == 200
    for b in r.json():
        if b["id"] == bid:
            return b
    return None


def patch_status(h, bid, status):
    r = requests.patch(f"{BASE_URL}/api/admin/bookings/{bid}", json={"status": status}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def consistency_check(stats):
    rev = stats["revenue"]
    rbs = stats["revenue_by_status"]
    by_offer = stats["by_offer"]
    total_calc = rbs["confirmed"] + rbs["completed"] + by_offer["gift"]
    assert abs(rev["total"] - total_calc) < 0.01, f"total mismatch: {rev['total']} vs {total_calc}"
    assert rev["month"] <= rev["total"] + 0.01
    assert rev["today"] <= rev["month"] + 0.01


def test_full_lifecycle(h):
    booking = get_booking(h, BOOKING_ID)
    assert booking is not None, "target booking not found"
    original_status = booking["status"]
    amount = 290.0
    today_iso = datetime.now(timezone.utc).date().isoformat()
    assert booking["date"][:10] != today_iso, "target booking should NOT have today's session date"

    # baseline: ensure pending
    if original_status != "pending":
        patch_status(h, BOOKING_ID, "pending")

    s0 = get_stats(h)
    consistency_check(s0)
    r0 = s0["revenue"]
    c0 = s0.get("confirmations", {"today": 0, "month": 0})
    sess_today0 = s0["sessions"]["today"]

    # PATCH -> confirmed
    resp = patch_status(h, BOOKING_ID, "confirmed")
    assert resp.get("confirmed_at", "").startswith(today_iso), f"confirmed_at missing/wrong: {resp.get('confirmed_at')}"

    s1 = get_stats(h)
    consistency_check(s1)
    assert abs((s1["revenue"]["today"] - r0["today"]) - amount) < 0.01, f"today revenue delta {s1['revenue']['today']-r0['today']} != {amount}"
    assert abs((s1["revenue"]["month"] - r0["month"]) - amount) < 0.01
    assert abs((s1["revenue"]["total"] - r0["total"]) - amount) < 0.01
    assert s1["confirmations"]["today"] - c0["today"] == 1
    assert s1["confirmations"]["month"] - c0["month"] == 1
    assert s1["sessions"]["today"] == sess_today0, "sessions.today should be unchanged (session date is 2026-06-15)"

    # PATCH -> completed: revenue unchanged, confirmed_at unchanged
    confirmed_at_1 = resp["confirmed_at"]
    resp2 = patch_status(h, BOOKING_ID, "completed")
    assert resp2["confirmed_at"] == confirmed_at_1, "confirmed_at should not change"
    s2 = get_stats(h)
    consistency_check(s2)
    assert abs(s2["revenue"]["today"] - s1["revenue"]["today"]) < 0.01
    assert abs(s2["revenue"]["month"] - s1["revenue"]["month"]) < 0.01
    assert abs(s2["revenue"]["total"] - s1["revenue"]["total"]) < 0.01

    # PATCH -> cancelled: revenue drops by amount from confirmed baseline
    patch_status(h, BOOKING_ID, "cancelled")
    s3 = get_stats(h)
    consistency_check(s3)
    assert abs(s3["revenue"]["today"] - r0["today"]) < 0.01
    assert abs(s3["revenue"]["month"] - r0["month"]) < 0.01
    assert abs(s3["revenue"]["total"] - r0["total"]) < 0.01

    # Restore to pending
    patch_status(h, BOOKING_ID, "pending")
    s4 = get_stats(h)
    consistency_check(s4)
    assert abs(s4["revenue"]["today"] - r0["today"]) < 0.01
