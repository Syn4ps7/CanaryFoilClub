"""Iteration 16 — Stripe Payments (Flow A sandbox).

Covers:
- POST /api/payments/checkout for booking & voucher (200, checkout_url, session_id)
- GET  /api/payments/status/{session_id}
- Error paths: 404 unknown, 400 already confirmed/paid, 400 invalid kind, 400 amount=0
- Webhook signature check (400 on bad sig)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_AUTH = None  # set in fixture


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin", "password": "admin"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---------- Booking payments ----------

def _create_booking(payload_extra=None, participants=1):
    payload = {
        "name": "TEST Iter16 Stripe",
        "email": "delivered@resend.dev",
        "phone": "+34600000001",
        "experience": "discovery",
        "date": "2026-10-05",
        "participants": participants,
        "message": "test",
    }
    if payload_extra:
        payload.update(payload_extra)
    r = requests.post(f"{BASE_URL}/api/booking", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def test_booking_checkout_happy_path(s):
    booking = _create_booking()
    assert booking.get("amount", 0) == 145.0
    r = s.post(f"{BASE_URL}/api/payments/checkout", json={
        "kind": "booking", "ref_id": booking["id"], "origin_url": "https://example.com"
    }, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["checkout_url"].startswith("https://checkout.stripe.com"), data
    assert data["session_id"].startswith("cs_test_"), data
    pytest.session_id = data["session_id"]
    pytest.booking_id = booking["id"]


def test_status_pending(s):
    sid = pytest.session_id
    r = s.get(f"{BASE_URL}/api/payments/status/{sid}", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["session_id"] == sid
    assert d["kind"] == "booking"
    assert d["amount"] == 145.0
    assert d["payment_status"] in ("pending", "paid")  # webhook could race


def test_status_unknown_session_404(s):
    r = s.get(f"{BASE_URL}/api/payments/status/cs_test_unknown_xyz", timeout=15)
    assert r.status_code == 404


def test_invalid_kind(s):
    r = s.post(f"{BASE_URL}/api/payments/checkout", json={
        "kind": "bogus", "ref_id": "x", "origin_url": "https://example.com"
    }, timeout=15)
    assert r.status_code == 400


def test_amount_zero_booking(s, admin_token):
    # Create a voucher, mark it paid via admin, redeem via new booking (voucher_code) → amount 0
    v = requests.post(f"{BASE_URL}/api/vouchers", json={
        "experience": "discovery",
        "buyer_name": "TEST Iter16 Buyer",
        "buyer_email": "delivered@resend.dev",
        "recipient_name": "TEST Iter16 Recipient",
    }, timeout=20)
    assert v.status_code == 200, v.text
    vjson = v.json()
    vid = vjson["id"]
    code = vjson.get("code")
    # mark paid via admin
    rp = requests.patch(f"{BASE_URL}/api/admin/vouchers/{vid}",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"status": "paid"}, timeout=15)
    assert rp.status_code == 200, rp.text
    # create booking with voucher_code → amount should be 0
    b = requests.post(f"{BASE_URL}/api/booking", json={
        "name": "TEST Iter16 VoucherPaid",
        "email": "delivered@resend.dev",
        "phone": "+34600000002",
        "experience": "discovery",
        "date": "2026-10-06",
        "participants": 1,
        "voucher_code": code,
    }, timeout=30)
    assert b.status_code == 200, b.text
    bjson = b.json()
    assert bjson.get("amount", -1) == 0
    r = s.post(f"{BASE_URL}/api/payments/checkout", json={
        "kind": "booking", "ref_id": bjson["id"], "origin_url": "https://example.com"
    }, timeout=15)
    assert r.status_code == 400
    assert "aucun paiement" in r.text.lower() or "montant" in r.text.lower()
    pytest.zero_booking_id = bjson["id"]
    pytest.paid_voucher_id = vid


def test_already_confirmed_booking(s, admin_token):
    # Confirm via admin PATCH first, then try checkout again → 400
    bid = pytest.booking_id
    rp = requests.patch(f"{BASE_URL}/api/admin/bookings/{bid}",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"status": "confirmed"}, timeout=30)
    assert rp.status_code == 200, rp.text
    r = s.post(f"{BASE_URL}/api/payments/checkout", json={
        "kind": "booking", "ref_id": bid, "origin_url": "https://example.com"
    }, timeout=15)
    assert r.status_code == 400
    assert "confirm" in r.text.lower() or "déjà" in r.text.lower()


# ---------- Voucher payments ----------

def test_voucher_checkout_happy_path(s):
    v = requests.post(f"{BASE_URL}/api/vouchers", json={
        "experience": "discovery",
        "buyer_name": "TEST Iter16 VBuyer",
        "buyer_email": "delivered@resend.dev",
        "recipient_name": "TEST Iter16 VRecipient",
    }, timeout=20)
    assert v.status_code == 200, v.text
    vjson = v.json()
    vid = vjson["id"]
    r = s.post(f"{BASE_URL}/api/payments/checkout", json={
        "kind": "voucher", "ref_id": vid, "origin_url": "https://example.com"
    }, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["checkout_url"].startswith("https://checkout.stripe.com")
    assert data["session_id"].startswith("cs_test_")
    st = s.get(f"{BASE_URL}/api/payments/status/{data['session_id']}", timeout=10).json()
    assert st["kind"] == "voucher"
    assert st["payment_status"] in ("pending", "paid")
    pytest.voucher_id = vid
    pytest.voucher_session_id = data["session_id"]


def test_voucher_already_paid_400(s, admin_token):
    # pytest.paid_voucher_id was set to paid earlier
    vid = pytest.paid_voucher_id
    r = s.post(f"{BASE_URL}/api/payments/checkout", json={
        "kind": "voucher", "ref_id": vid, "origin_url": "https://example.com"
    }, timeout=15)
    assert r.status_code == 400


# ---------- Webhook signature ----------

def test_webhook_bad_signature(s):
    r = s.post(f"{BASE_URL}/api/stripe/webhook",
               data=b'{"id":"evt","type":"checkout.session.completed","data":{"object":{"id":"cs_test_x","payment_status":"paid"}}}',
               headers={"stripe-signature": "t=1,v1=bogus", "content-type": "application/json"},
               timeout=15)
    assert r.status_code == 400


# ---------- Cleanup ----------

def test_zzz_cleanup(admin_token):
    hdr = {"Authorization": f"Bearer {admin_token}"}
    for bid_attr in ("booking_id", "zero_booking_id"):
        bid = getattr(pytest, bid_attr, None)
        if bid:
            requests.patch(f"{BASE_URL}/api/admin/bookings/{bid}", headers=hdr,
                           json={"status": "cancelled"}, timeout=15)
    for vid_attr in ("voucher_id", "paid_voucher_id"):
        vid = getattr(pytest, vid_attr, None)
        if vid:
            requests.patch(f"{BASE_URL}/api/admin/vouchers/{vid}", headers=hdr,
                           json={"status": "cancelled"}, timeout=15)
