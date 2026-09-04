"""Iteration 6 backend tests: gift vouchers + review replies + booking regression."""
import os
import re
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
CODE_RE = re.compile(r"^CFC-[A-Z2-9]{4}-[A-Z2-9]{4}$")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": "admin", "password": "admin"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def H(token):
    return {"Authorization": f"Bearer {token}"}


# -------- Voucher creation (public) --------
class TestVoucherCreate:
    def test_create_discovery(self):
        r = requests.post(f"{API}/vouchers", json={
            "buyer_name": "TEST Buyer", "buyer_email": "delivered@resend.dev",
            "recipient_name": "TEST Recipient", "experience": "discovery",
            "participants": 3, "lang": "fr"}, timeout=30)
        assert r.status_code == 200, r.text
        v = r.json()
        assert CODE_RE.match(v["code"]), v["code"]
        assert v["status"] == "pending"
        assert v["value"] == 145 * 3
        assert v["participants"] == 3

    def test_create_duo_forces_2(self):
        r = requests.post(f"{API}/vouchers", json={
            "buyer_name": "TEST Duo", "buyer_email": "delivered@resend.dev",
            "recipient_name": "TEST Duo R", "experience": "duo",
            "participants": 1, "lang": "fr"}, timeout=30)
        assert r.status_code == 200
        v = r.json()
        assert v["participants"] == 2
        assert v["value"] == 280

    def test_invalid_email(self):
        r = requests.post(f"{API}/vouchers", json={
            "buyer_name": "X", "buyer_email": "notanemail",
            "recipient_name": "Y", "experience": "discovery", "participants": 1}, timeout=15)
        assert r.status_code == 422

    def test_corporate_falls_back(self):
        r = requests.post(f"{API}/vouchers", json={
            "buyer_name": "TEST Corp", "buyer_email": "delivered@resend.dev",
            "recipient_name": "TEST R", "experience": "corporate", "participants": 2}, timeout=30)
        assert r.status_code == 200
        v = r.json()
        assert v["experience"] == "discovery"
        assert v["value"] == 145 * 2


# -------- Check code (public) --------
class TestVoucherCheck:
    def test_unknown(self):
        r = requests.get(f"{API}/vouchers/check/CFC-ZZZZ-ZZZZ", timeout=15)
        assert r.status_code == 200
        assert r.json() == {"valid": False, "reason": "not_found"}

    def test_pending_unpaid(self):
        c = requests.post(f"{API}/vouchers", json={
            "buyer_name": "TEST P", "buyer_email": "delivered@resend.dev",
            "recipient_name": "TEST P R", "experience": "discovery", "participants": 1}, timeout=30).json()
        r = requests.get(f"{API}/vouchers/check/{c['code']}", timeout=15)
        assert r.status_code == 200
        assert r.json()["valid"] is False
        assert r.json()["reason"] == "unpaid"


# -------- Admin activate / cancel / resend --------
class TestAdminVouchers:
    def _make(self):
        return requests.post(f"{API}/vouchers", json={
            "buyer_name": "TEST Admin", "buyer_email": "delivered@resend.dev",
            "recipient_name": "TEST R", "experience": "discovery", "participants": 1}, timeout=30).json()

    def test_no_token_401(self):
        v = self._make()
        r = requests.patch(f"{API}/admin/vouchers/{v['id']}", json={"status": "paid"}, timeout=15)
        assert r.status_code == 401

    def test_unknown_404(self, H):
        r = requests.patch(f"{API}/admin/vouchers/nope", json={"status": "paid"}, headers=H, timeout=15)
        assert r.status_code == 404

    def test_invalid_status_400(self, H):
        v = self._make()
        r = requests.patch(f"{API}/admin/vouchers/{v['id']}", json={"status": "weird"}, headers=H, timeout=15)
        assert r.status_code == 400

    def test_activate_flow(self, H):
        v = self._make()
        r = requests.patch(f"{API}/admin/vouchers/{v['id']}", json={"status": "paid"}, headers=H, timeout=40)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["status"] == "paid"
        assert p["paid_at"] and p["expires_at"]
        assert p["email_sent"] is True
        # case-insensitive/space tolerant check
        code_with_space = " " + p["code"].lower() + " "
        chk = requests.get(f"{API}/vouchers/check/{code_with_space}", timeout=15).json()
        assert chk["valid"] is True
        assert chk["value"] == p["value"]
        assert chk["recipient_name"] == "TEST R"

    def test_resend_pending_400(self, H):
        v = self._make()
        r = requests.post(f"{API}/admin/vouchers/{v['id']}/resend", headers=H, timeout=15)
        assert r.status_code == 400

    def test_cancel_then_check(self, H):
        v = self._make()
        r = requests.patch(f"{API}/admin/vouchers/{v['id']}", json={"status": "cancelled"}, headers=H, timeout=15)
        assert r.status_code == 200 and r.json()["status"] == "cancelled"
        chk = requests.get(f"{API}/vouchers/check/{v['code']}", timeout=15).json()
        assert chk["reason"] == "cancelled"

    def test_list(self, H):
        r = requests.get(f"{API}/admin/vouchers", headers=H, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list) and len(r.json()) >= 1


# -------- Booking redemption --------
class TestBookingRedemption:
    def _paid_voucher(self, H):
        v = requests.post(f"{API}/vouchers", json={
            "buyer_name": "TEST BR", "buyer_email": "delivered@resend.dev",
            "recipient_name": "TEST BR R", "experience": "discovery", "participants": 1}, timeout=30).json()
        requests.patch(f"{API}/admin/vouchers/{v['id']}", json={"status": "paid"}, headers=H, timeout=40)
        return v

    def test_booking_with_paid_voucher(self, H):
        v = self._paid_voucher(H)
        payload = {"name": "TEST Book", "email": "delivered@resend.dev", "phone": "+34600111222",
                   "experience": "discovery", "date": "2026-06-01", "participants": 1,
                   "voucher_code": v["code"].lower(), "lang": "fr"}
        r = requests.post(f"{API}/booking", json=payload, timeout=60)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["voucher_code"] == v["code"]
        assert b["discount"] == 145
        assert b["amount"] == 0
        assert "created_at" in b and b["created_at"]

        # reuse -> 400
        r2 = requests.post(f"{API}/booking", json=payload, timeout=60)
        assert r2.status_code == 400
        assert "utilisé" in r2.text.lower() or "utilis" in r2.text

    def test_booking_unknown_code(self):
        r = requests.post(f"{API}/booking", json={
            "name": "TEST U", "email": "delivered@resend.dev", "phone": "+34600111222",
            "experience": "discovery", "date": "2026-06-01", "participants": 1,
            "voucher_code": "CFC-XXXX-YYYY"}, timeout=60)
        assert r.status_code == 400
        assert "introuvable" in r.text.lower()

    def test_booking_pending_code(self):
        v = requests.post(f"{API}/vouchers", json={
            "buyer_name": "TEST BP", "buyer_email": "delivered@resend.dev",
            "recipient_name": "TEST BP R", "experience": "discovery", "participants": 1}, timeout=30).json()
        r = requests.post(f"{API}/booking", json={
            "name": "TEST BP", "email": "delivered@resend.dev", "phone": "+34600111222",
            "experience": "discovery", "date": "2026-06-01", "participants": 1,
            "voucher_code": v["code"]}, timeout=60)
        assert r.status_code == 400

    def test_booking_without_voucher_regression(self):
        r = requests.post(f"{API}/booking", json={
            "name": "TEST NoV", "email": "delivered@resend.dev", "phone": "+34600111222",
            "experience": "discovery", "date": "2026-06-01", "participants": 1}, timeout=60)
        assert r.status_code == 200, r.text
        b = r.json()
        assert "created_at" in b and b["created_at"]
        assert b.get("voucher_code") in (None, "")

    def test_release_redeemed(self, H):
        v = self._paid_voucher(H)
        r = requests.post(f"{API}/booking", json={
            "name": "TEST Rel", "email": "delivered@resend.dev", "phone": "+34600111222",
            "experience": "discovery", "date": "2026-06-01", "participants": 1,
            "voucher_code": v["code"]}, timeout=60)
        assert r.status_code == 200
        chk = requests.get(f"{API}/vouchers/check/{v['code']}", timeout=15).json()
        assert chk["reason"] == "redeemed"
        # Release by setting paid again
        r2 = requests.patch(f"{API}/admin/vouchers/{v['id']}", json={"status": "paid"}, headers=H, timeout=40)
        assert r2.status_code == 200
        chk2 = requests.get(f"{API}/vouchers/check/{v['code']}", timeout=15).json()
        assert chk2["valid"] is True


# -------- Stats + CSV --------
class TestStatsAndCsv:
    def test_stats_shape(self, H):
        r = requests.get(f"{API}/admin/stats", headers=H, timeout=15)
        assert r.status_code == 200, r.text
        s = r.json()
        assert "gift" in s["by_offer"]
        assert "vouchers" in s
        for k in ("pending", "active", "outstanding"):
            assert k in s["vouchers"]

    def test_csv_headers(self, H):
        r = requests.get(f"{API}/admin/bookings/export.csv", headers=H, timeout=15)
        assert r.status_code == 200
        head = r.text.splitlines()[0]
        assert "bon_cadeau" in head
        assert "remise_eur" in head


# -------- Review replies --------
class TestReviewReplies:
    @pytest.fixture(scope="class")
    def review_id(self, H):
        rs = requests.get(f"{API}/admin/reviews", headers=H, timeout=15).json()
        assert rs, "No reviews present"
        return rs[0]["id"]

    def test_admin_reviews_serialises(self, H):
        r = requests.get(f"{API}/admin/reviews", headers=H, timeout=15)
        assert r.status_code == 200

    def test_set_reply(self, H, review_id):
        r = requests.patch(f"{API}/admin/reviews/{review_id}", json={"reply": "TEST Merci pour votre avis !"},
                           headers=H, timeout=15)
        assert r.status_code == 200
        assert r.json()["reply"] == "TEST Merci pour votre avis !"
        assert r.json()["replied_at"]
        pub = requests.get(f"{API}/reviews", timeout=15).json()
        assert any(rv["id"] == review_id and rv.get("reply") for rv in pub)

    def test_clear_reply_then_restore(self, H, review_id):
        r = requests.patch(f"{API}/admin/reviews/{review_id}", json={"reply": ""}, headers=H, timeout=15)
        assert r.status_code == 200
        assert r.json()["reply"] is None
        assert r.json()["replied_at"] is None
        # restore non-empty for spec
        requests.patch(f"{API}/admin/reviews/{review_id}",
                       json={"reply": "Merci pour votre confiance, à très vite sur l'eau !"},
                       headers=H, timeout=15)
