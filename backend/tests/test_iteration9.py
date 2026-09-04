"""Iteration 9 — voucher PDF download tests."""
import os
import re
import time
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
BASE = BASE.rstrip("/")
API = f"{BASE}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": "admin", "password": "admin"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def created_voucher():
    payload = {
        "experience": "duo",
        "participants": 2,
        "lang": "fr",
        "buyer_name": "TEST Buyer",
        "buyer_email": "delivered@resend.dev",
        "recipient_name": "TEST Recipient",
        "message": "Bon vol !",
    }
    r = requests.post(f"{API}/vouchers", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    v = r.json()
    return v


def test_create_returns_download_token(created_voucher):
    assert "download_token" in created_voucher
    assert isinstance(created_voucher["download_token"], str)
    assert len(created_voucher["download_token"]) >= 16


def test_pdf_pending_returns_403(created_voucher):
    code = created_voucher["code"]
    tok = created_voucher["download_token"]
    r = requests.get(f"{API}/vouchers/{code}/pdf", params={"k": tok}, timeout=30)
    assert r.status_code == 403, r.text


def test_pdf_wrong_token_returns_404(created_voucher):
    code = created_voucher["code"]
    r = requests.get(f"{API}/vouchers/{code}/pdf", params={"k": "a" * 32}, timeout=30)
    assert r.status_code == 404, r.text


def test_pdf_short_token_returns_422(created_voucher):
    code = created_voucher["code"]
    r = requests.get(f"{API}/vouchers/{code}/pdf", params={"k": "abc"}, timeout=30)
    assert r.status_code == 422, r.text


def test_paid_pdf_download(admin_token, created_voucher):
    vid = created_voucher["id"]
    code = created_voucher["code"]
    tok = created_voucher["download_token"]
    # Mark paid
    r = requests.patch(f"{API}/admin/vouchers/{vid}", json={"status": "paid"},
                       headers={"Authorization": f"Bearer {admin_token}"}, timeout=60)
    assert r.status_code == 200, r.text
    assert r.json().get("email_sent") is True

    # Download PDF via public endpoint (case-insensitive code)
    r = requests.get(f"{API}/vouchers/{code.lower()}/pdf", params={"k": tok}, timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content.startswith(b"%PDF")
    cd = r.headers.get("content-disposition", "")
    assert f"bon-cadeau-{code}.pdf" in cd, cd
    assert len(r.content) > 3 * 1024


def test_admin_pdf_pending_ok(admin_token):
    # Create fresh pending voucher
    payload = {
        "experience": "discovery", "participants": 1, "lang": "fr",
        "buyer_name": "TEST Buyer2", "buyer_email": "delivered@resend.dev",
        "recipient_name": "TEST Recipient2",
    }
    r = requests.post(f"{API}/vouchers", json=payload, timeout=30)
    assert r.status_code == 200
    vid = r.json()["id"]

    # Admin PDF works while pending
    r = requests.get(f"{API}/admin/vouchers/{vid}/pdf",
                     headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")


def test_admin_pdf_unauth():
    # arbitrary id
    r = requests.get(f"{API}/admin/vouchers/nonexistent-id/pdf", timeout=30)
    assert r.status_code == 401


def test_admin_pdf_unknown_id(admin_token):
    r = requests.get(f"{API}/admin/vouchers/does-not-exist-id/pdf",
                     headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
    assert r.status_code == 404


def test_build_voucher_email_contains_pdf_link():
    # Run in-process
    import sys
    sys.path.insert(0, "/app/backend")
    from emailer import build_voucher_email
    s, h = build_voucher_email({
        "lang": "fr", "experience": "duo", "participants": 2, "value": 280.0,
        "expires_at": "2027-01-01T00:00:00+00:00", "recipient_name": "J",
        "buyer_name": "C", "buyer_email": "x", "code": "CFC-AAAA-BBBB", "id": "x",
    }, "https://example.com/api/vouchers/CFC-AAAA-BBBB/pdf?k=abc")
    assert "https://example.com/api/vouchers" in h
    assert "PDF" in h
