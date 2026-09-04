"""Iteration 5 backend tests — reviews (public + admin) and weekly report."""
import os
import uuid
import pytest
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pymongo import MongoClient


def _load_env(path, key):
    try:
        with open(path) as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        return None


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_env("/app/frontend/.env", "REACT_APP_BACKEND_URL") or "").rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL") or _load_env("/app/backend/.env", "MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or _load_env("/app/backend/.env", "DB_NAME")
TZ = ZoneInfo("Atlantic/Canary")


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": "admin", "password": "admin"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture
def h(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


# ---------- Review request ----------
class TestReviewRequest:
    def test_unknown_booking_404(self, h):
        r = requests.post(f"{API}/admin/bookings/nope-xyz/review-request", headers=h, timeout=15)
        assert r.status_code == 404

    def test_pending_400(self, h, db):
        b = db.bookings.find_one({"status": "pending"})
        if not b:
            pytest.skip("no pending booking")
        r = requests.post(f"{API}/admin/bookings/{b['id']}/review-request", headers=h, timeout=15)
        assert r.status_code == 400

    def test_confirmed_delivered_ok(self, h, db):
        # Use the TEST Regression booking (delivered@resend.dev, per context)
        b = db.bookings.find_one({"name": {"$regex": "TEST Regression"}, "email": "delivered@resend.dev"})
        if not b:
            b = db.bookings.find_one({"email": "delivered@resend.dev", "name": {"$ne": "Laura Gomez"}})
        assert b, "need a delivered@resend.dev booking that is not Laura Gomez"
        bid = b["id"]
        orig = {k: b.get(k) for k in ("status", "review_request_sent", "review_request_sent_at", "review_token")}
        db.bookings.update_one({"id": bid}, {"$set": {"status": "confirmed"},
                                             "$unset": {"review_request_sent": "", "review_request_sent_at": ""}})
        try:
            r = requests.post(f"{API}/admin/bookings/{bid}/review-request", headers=h, timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["review_request_sent"] is True
            after = db.bookings.find_one({"id": bid})
            assert after.get("review_token")
        finally:
            restore = {k: v for k, v in orig.items() if v is not None}
            unset = {k: "" for k, v in orig.items() if v is None}
            op = {}
            if restore:
                op["$set"] = restore
            if unset:
                op["$unset"] = unset
            if op:
                db.bookings.update_one({"id": bid}, op)


# ---------- Public review endpoints ----------
class TestPublicReview:
    def test_bad_token(self):
        r = requests.get(f"{API}/reviews/badtoken-xyz", timeout=10)
        assert r.status_code == 404

    def test_full_flow(self, h, db):
        # Pick a fresh delivered@resend.dev booking (not Laura), issue review request to get token,
        # then GET/POST as public. Cleanup: delete created review + restore booking flags.
        b = db.bookings.find_one({"email": "delivered@resend.dev", "name": {"$ne": "Laura Gomez"}})
        assert b, "need a delivered@resend.dev booking that is not Laura"
        bid = b["id"]
        orig = {k: b.get(k) for k in ("status", "review_request_sent", "review_request_sent_at",
                                       "review_token", "review_id", "lang")}
        db.bookings.update_one({"id": bid},
                               {"$set": {"status": "confirmed"},
                                "$unset": {"review_request_sent": "", "review_request_sent_at": "",
                                           "review_token": "", "review_id": ""}})
        # ensure no orphan review
        db.reviews.delete_many({"booking_id": bid})
        try:
            r = requests.post(f"{API}/admin/bookings/{bid}/review-request", headers=h, timeout=30)
            assert r.status_code == 200, r.text
            token = db.bookings.find_one({"id": bid})["review_token"]

            # GET context
            g = requests.get(f"{API}/reviews/{token}", timeout=10)
            assert g.status_code == 200
            ctx = g.json()
            assert ctx["already_reviewed"] is False
            assert ctx["review"] is None
            assert "name" in ctx and "experience" in ctx and "date" in ctx and "lang" in ctx
            # name should be first name only
            assert " " not in ctx["name"] or len(ctx["name"].split()) == 1

            # invalid rating
            r422 = requests.post(f"{API}/reviews/{token}", json={"rating": 6, "comment": "great session"}, timeout=15)
            assert r422.status_code == 422

            # too short comment
            r422b = requests.post(f"{API}/reviews/{token}", json={"rating": 4, "comment": "ok"}, timeout=15)
            assert r422b.status_code == 422

            # valid submission
            payload = {"rating": 4, "comment": "TEST comment automated integration test", "display_name": "TEST Auto"}
            rp = requests.post(f"{API}/reviews/{token}", json=payload, timeout=15)
            assert rp.status_code in (200, 201), rp.text
            review = rp.json()
            assert review["rating"] == 4
            assert review["approved"] is False
            assert review["name"] == "TEST Auto"
            review_id = review["id"]

            # booking now has review_id
            after = db.bookings.find_one({"id": bid})
            assert after.get("review_id") == review_id

            # second submission → 409
            rp2 = requests.post(f"{API}/reviews/{token}", json=payload, timeout=15)
            assert rp2.status_code == 409

            # GET again → already_reviewed
            g2 = requests.get(f"{API}/reviews/{token}", timeout=10).json()
            assert g2["already_reviewed"] is True
            assert g2["review"] is not None

            # cleanup: delete review
            dr = requests.delete(f"{API}/admin/reviews/{review_id}", headers=h, timeout=15)
            assert dr.status_code == 200
        finally:
            restore = {k: v for k, v in orig.items() if v is not None}
            unset = {k: "" for k, v in orig.items() if v is None}
            op = {}
            if restore:
                op["$set"] = restore
            if unset:
                op["$unset"] = unset
            if op:
                db.bookings.update_one({"id": bid}, op)
            db.reviews.delete_many({"booking_id": bid, "name": "TEST Auto"})


# ---------- Public + admin listing / moderation ----------
class TestReviewListing:
    def test_public_only_approved_sorted(self):
        r = requests.get(f"{API}/reviews", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        for rv in data:
            assert rv.get("approved") is True
        # featured first
        if len(data) >= 2:
            featured_seen_after_non_featured = False
            saw_non_featured = False
            for rv in data:
                if not rv.get("featured"):
                    saw_non_featured = True
                elif saw_non_featured:
                    featured_seen_after_non_featured = True
            assert not featured_seen_after_non_featured, "featured reviews must come first"

    def test_admin_reviews_no_token_401(self):
        r = requests.get(f"{API}/admin/reviews", timeout=10)
        assert r.status_code == 401

    def test_patch_empty_body_400(self, h, db):
        rv = db.reviews.find_one({})
        if not rv:
            pytest.skip("no review to patch")
        r = requests.patch(f"{API}/admin/reviews/{rv['id']}", headers=h, json={}, timeout=15)
        assert r.status_code == 400

    def test_patch_unknown_404(self, h):
        r = requests.patch(f"{API}/admin/reviews/nope-xyz", headers=h, json={"approved": True}, timeout=15)
        assert r.status_code == 404

    def test_delete_unknown_404(self, h):
        r = requests.delete(f"{API}/admin/reviews/nope-xyz", headers=h, timeout=15)
        assert r.status_code == 404

    def test_patch_toggle_hides_from_public(self, h, db):
        # Use the existing approved Laura G. review (don't delete). Toggle off, verify, toggle back.
        rv = db.reviews.find_one({"approved": True, "name": {"$regex": "Laura"}})
        if not rv:
            pytest.skip("no Laura G. approved review present")
        rid = rv["id"]
        try:
            r = requests.patch(f"{API}/admin/reviews/{rid}", headers=h, json={"approved": False}, timeout=15)
            assert r.status_code == 200 and r.json()["approved"] is False
            pub = requests.get(f"{API}/reviews", timeout=10).json()
            assert not any(x["id"] == rid for x in pub)
        finally:
            requests.patch(f"{API}/admin/reviews/{rid}", headers=h, json={"approved": True}, timeout=15)
        pub = requests.get(f"{API}/reviews", timeout=10).json()
        assert any(x["id"] == rid for x in pub)


# ---------- Batch review-requests run ----------
class TestReviewsRun:
    def test_run_idempotent_yesterday(self, h, db):
        yesterday = (datetime.now(TZ) - timedelta(days=1)).date().isoformat()
        b = db.bookings.find_one({"email": "delivered@resend.dev", "name": {"$ne": "Laura Gomez"}})
        assert b
        bid = b["id"]
        orig = {k: b.get(k) for k in ("date", "status", "review_request_sent", "review_request_sent_at", "review_token")}
        db.bookings.update_one(
            {"id": bid},
            {"$set": {"date": yesterday, "status": "completed"},
             "$unset": {"review_request_sent": "", "review_request_sent_at": ""}},
        )
        try:
            r1 = requests.post(f"{API}/admin/reviews/run", headers=h, timeout=60)
            assert r1.status_code == 200, r1.text
            d1 = r1.json()
            assert d1["date"] == yesterday
            assert d1["sent"] >= 1
            r2 = requests.post(f"{API}/admin/reviews/run", headers=h, timeout=30)
            assert r2.status_code == 200
            d2 = r2.json()
            assert d2["sent"] == 0
        finally:
            restore = {k: v for k, v in orig.items() if v is not None}
            unset = {k: "" for k, v in orig.items() if v is None}
            op = {}
            if restore:
                op["$set"] = restore
            if unset:
                op["$unset"] = unset
            if op:
                db.bookings.update_one({"id": bid}, op)


# ---------- Weekly report ----------
class TestWeeklyReport:
    def test_preview_shape(self, h):
        r = requests.get(f"{API}/admin/reports/weekly", headers=h, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("week_start", "week_end", "week_label", "revenue", "sessions", "occupancy",
                  "commissions", "empty_days", "pending_total", "by_offer", "days", "next_days",
                  "reviews", "avg_rating"):
            assert k in d, f"missing {k}"
        assert len(d["days"]) == 7
        assert len(d["next_days"]) == 7
        assert len(d["by_offer"]) == 3
        # week_start is last Monday
        ws = datetime.fromisoformat(d["week_start"]).date()
        today = datetime.now(TZ).date()
        last_monday = today - timedelta(days=today.weekday() + 7)
        assert ws == last_monday
        # revenue == sum(days.revenue)
        s = sum(x["revenue"] for x in d["days"])
        assert abs(d["revenue"] - s) < 0.01
        # per-day fields
        for day in d["days"]:
            for k in ("label", "sessions", "revenue", "occupancy"):
                assert k in day
        for nd in d["next_days"]:
            assert "pending" in nd
        assert "last_sent" in d

    def test_no_token_401(self):
        r = requests.get(f"{API}/admin/reports/weekly", timeout=10)
        assert r.status_code == 401

    def test_send_delivered_ok(self, h):
        r = requests.post(f"{API}/admin/reports/weekly/send", headers=h,
                          params={"to": "delivered@resend.dev"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["sent"] is True
        assert d.get("to") == "delivered@resend.dev"

    def test_send_default_owner_undeliverable_502(self, h):
        r = requests.post(f"{API}/admin/reports/weekly/send", headers=h, timeout=45)
        # OWNER_EMAIL is bookings@canaryfoilclub.com — undeliverable → 502
        assert r.status_code == 502, f"expected 502, got {r.status_code}: {r.text[:200]}"

    def test_send_invalid_to_422(self, h):
        r = requests.post(f"{API}/admin/reports/weekly/send", headers=h,
                          params={"to": "not-an-email"}, timeout=15)
        assert r.status_code == 422
