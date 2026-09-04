"""Iteration 15: Parental authorisation (minor) — backend tests."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_CREDS = {"email": "admin", "password": "admin"}
TEST_EMAIL = "delivered@resend.dev"
TEST_DATE = "2026-10-01"

created_ids = []


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json=ADMIN_CREDS, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _booking_payload(**over):
    p = {
        "name": "TEST Iter15",
        "email": TEST_EMAIL,
        "phone": "+34600000000",
        "date": TEST_DATE,
        "experience": "discovery",
        "participants": 1,
        "lang": "fr",
    }
    p.update(over)
    return p


# ---- POST /api/booking : minor validation ----

def test_minor_true_without_consent_returns_400():
    r = requests.post(f"{API}/booking", json=_booking_payload(minor=True, minor_consent=False), timeout=30)
    assert r.status_code == 400, r.text
    detail = r.json().get("detail", "")
    assert "autorisation parentale" in detail.lower() or "mineur" in detail.lower(), detail


def test_minor_true_with_consent_returns_200():
    r = requests.post(f"{API}/booking", json=_booking_payload(minor=True, minor_consent=True), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["minor"] is True
    assert data["minor_consent"] is True
    assert data.get("parental_auth_received") in (None, False)
    created_ids.append(data["id"])


def test_minor_false_default_returns_200():
    r = requests.post(f"{API}/booking", json=_booking_payload(), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["minor"] is False
    created_ids.append(data["id"])


# ---- PATCH /api/admin/bookings/{id} : parental_auth_received ----

def test_patch_parental_auth_received_true(auth_headers):
    assert created_ids, "prerequisite booking missing"
    bid = created_ids[0]
    r = requests.patch(f"{API}/admin/bookings/{bid}", headers=auth_headers,
                       json={"parental_auth_received": True}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("parental_auth_received") is True


def test_patch_parental_auth_received_false(auth_headers):
    bid = created_ids[0]
    r = requests.patch(f"{API}/admin/bookings/{bid}", headers=auth_headers,
                       json={"parental_auth_received": False}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("parental_auth_received") is False


def test_admin_list_bookings_contains_fields(auth_headers):
    r = requests.get(f"{API}/admin/bookings?limit=200", headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else data.get("items", data.get("bookings", []))
    ours = [b for b in items if b.get("id") in created_ids]
    assert len(ours) >= 1
    minor_b = next((b for b in ours if b["id"] == created_ids[0]), None)
    assert minor_b is not None
    assert "minor" in minor_b and "minor_consent" in minor_b and "parental_auth_received" in minor_b
    assert minor_b["minor"] is True
    assert minor_b["minor_consent"] is True


# ---- Cleanup: cancel test bookings ----

def test_zzz_cleanup_cancel(auth_headers):
    for bid in created_ids:
        r = requests.patch(f"{API}/admin/bookings/{bid}", headers=auth_headers,
                           json={"status": "cancelled"}, timeout=15)
        assert r.status_code == 200, f"cleanup failed for {bid}: {r.text}"
