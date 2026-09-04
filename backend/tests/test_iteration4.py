"""Backend tests for Canary Foil Club — iteration 4:
slot_times in settings/planning, meeting-point endpoints, reminder endpoints, confirmation email slot inclusion."""
import os
import pytest
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pymongo import MongoClient


def _load_frontend_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return None


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env() or "").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin"
ADMIN_PASSWORD = "admin"
TZ_CANARY = ZoneInfo("Atlantic/Canary")


def _load_backend_env(k):
    try:
        with open("/app/backend/.env") as f:
            for line in f:
                if line.startswith(f"{k}="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return None


MONGO_URL = os.environ.get("MONGO_URL") or _load_backend_env("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or _load_backend_env("DB_NAME")


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def db():
    c = MongoClient(MONGO_URL)
    return c[DB_NAME]


DEFAULT_TIMES = ["09:00", "10:30", "12:00", "13:30", "15:00", "16:30"]


# --- Settings slot_times ---
class TestSettingsSlotTimes:
    def test_get_settings_has_slot_times(self, auth_headers):
        r = requests.get(f"{API}/admin/settings", headers=auth_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "slot_times" in d
        assert len(d["slot_times"]) == d["slots_per_day"]
        for t in d["slot_times"]:
            assert len(t) == 5 and t[2] == ":"

    def test_put_settings_invalid_entries_dropped_and_padded(self, auth_headers):
        r = requests.put(f"{API}/admin/settings", headers=auth_headers,
                         json={"boards": 3, "slots_per_day": 4, "slot_times": ["09:00", "11:00", "bad", "15:30"]},
                         timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["slots_per_day"] == 4
        assert len(d["slot_times"]) == 4
        # valid entries kept; "bad" dropped; padded from last valid +90min = 17:00
        assert d["slot_times"][0] == "09:00"
        assert d["slot_times"][1] == "11:00"
        assert d["slot_times"][2] == "15:30"
        assert d["slot_times"][3] == "17:00"

    def test_put_settings_no_slot_times_defaults(self, auth_headers):
        r = requests.put(f"{API}/admin/settings", headers=auth_headers,
                         json={"boards": 3, "slots_per_day": 6}, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["slot_times"] == DEFAULT_TIMES

    def test_restore_defaults(self, auth_headers):
        r = requests.put(f"{API}/admin/settings", headers=auth_headers,
                         json={"boards": 3, "slots_per_day": 6, "slot_times": DEFAULT_TIMES}, timeout=10)
        assert r.status_code == 200
        assert r.json()["slot_times"] == DEFAULT_TIMES


# --- Planning includes slot_times ---
class TestPlanningSlotTimes:
    def test_planning_has_slot_times(self, auth_headers):
        today = datetime.now(TZ_CANARY).date().isoformat()
        r = requests.get(f"{API}/admin/planning", headers=auth_headers, params={"day": today}, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "slot_times" in d
        assert len(d["slot_times"]) == d["slots_per_day"]


# --- Meeting Point ---
class TestMeetingPoint:
    def test_get_meeting_point(self, auth_headers):
        day = (datetime.now(TZ_CANARY).date() + timedelta(days=2)).isoformat()
        r = requests.get(f"{API}/admin/planning/meeting-point", headers=auth_headers, params={"day": day}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["date"] == day
        assert d["source"] in ("weather", "override", "default")
        assert "spot" in d
        assert "address" in d
        assert "summary" in d
        assert "options" in d and len(d["options"]) == 4
        assert d["reminder_hour"] == 17

    def test_put_meeting_point_override_autofill_address(self, auth_headers):
        day = (datetime.now(TZ_CANARY).date() + timedelta(days=3)).isoformat()
        r = requests.put(f"{API}/admin/planning/meeting-point", headers=auth_headers,
                         json={"date": day, "spot": "La Caleta / Playa Paraíso"}, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["source"] == "override"
        assert d["spot"] == "La Caleta / Playa Paraíso"
        assert "La Caleta" in d["address"]

    def test_put_meeting_point_custom_address_kept(self, auth_headers):
        day = (datetime.now(TZ_CANARY).date() + timedelta(days=4)).isoformat()
        r = requests.put(f"{API}/admin/planning/meeting-point", headers=auth_headers,
                         json={"date": day, "spot": "El Puertito de Adeje", "address": "Custom access note"},
                         timeout=10)
        assert r.status_code == 200
        assert r.json()["address"] == "Custom access note"

    def test_put_meeting_point_reset(self, auth_headers):
        day = (datetime.now(TZ_CANARY).date() + timedelta(days=3)).isoformat()
        r = requests.put(f"{API}/admin/planning/meeting-point", headers=auth_headers,
                         json={"date": day, "spot": None}, timeout=15)
        assert r.status_code == 200
        assert r.json()["source"] in ("weather", "default")

    def test_meeting_point_invalid_date(self, auth_headers):
        r = requests.put(f"{API}/admin/planning/meeting-point", headers=auth_headers,
                         json={"date": "not-a-date", "spot": "El Puertito de Adeje"}, timeout=10)
        assert r.status_code == 400

    def test_meeting_point_no_token(self):
        r = requests.get(f"{API}/admin/planning/meeting-point", timeout=10)
        assert r.status_code == 401

    def test_cleanup(self, auth_headers):
        for d in range(2, 6):
            day = (datetime.now(TZ_CANARY).date() + timedelta(days=d)).isoformat()
            requests.put(f"{API}/admin/planning/meeting-point", headers=auth_headers,
                         json={"date": day, "spot": None}, timeout=10)


# --- Reminder endpoints ---
class TestReminders:
    def test_reminder_unknown_id_404(self, auth_headers):
        r = requests.post(f"{API}/admin/bookings/nonexistent-xyz/reminder", headers=auth_headers, timeout=10)
        assert r.status_code == 404

    def test_reminder_pending_400(self, auth_headers):
        # find a pending booking
        r = requests.get(f"{API}/admin/bookings", headers=auth_headers, params={"status": "pending"}, timeout=10)
        assert r.status_code == 200
        items = r.json()
        if not items:
            pytest.skip("No pending bookings to test")
        bid = items[0]["id"]
        r = requests.post(f"{API}/admin/bookings/{bid}/reminder", headers=auth_headers, timeout=15)
        assert r.status_code == 400

    def test_reminder_confirmed_delivered(self, auth_headers, db):
        # find a booking with delivered@resend.dev
        booking = db.bookings.find_one({"email": "delivered@resend.dev"})
        assert booking, "No delivered@resend.dev booking seeded"
        bid = booking["id"]
        original_status = booking.get("status")
        original_reminder = {k: booking.get(k) for k in ("reminder_sent", "reminder_sent_at", "reminder_spot")}
        # Force confirmed
        db.bookings.update_one({"id": bid}, {"$set": {"status": "confirmed"}, "$unset": {"reminder_sent": ""}})
        try:
            r = requests.post(f"{API}/admin/bookings/{bid}/reminder", headers=auth_headers, timeout=30)
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["reminder_sent"] is True
            assert d.get("reminder_sent_at")
            assert d.get("reminder_spot")
        finally:
            restore = {"status": original_status}
            unset = {}
            for k, v in original_reminder.items():
                if v is None:
                    unset[k] = ""
                else:
                    restore[k] = v
            op = {"$set": restore}
            if unset:
                op["$unset"] = unset
            db.bookings.update_one({"id": bid}, op)

    def test_reminder_confirmed_undeliverable_502(self, auth_headers, db):
        # find example.com booking
        booking = db.bookings.find_one({"email": {"$regex": "example"}, "status": {"$in": ["confirmed", "pending"]}})
        if not booking:
            pytest.skip("No example.com booking to test")
        bid = booking["id"]
        original_status = booking.get("status")
        db.bookings.update_one({"id": bid}, {"$set": {"status": "confirmed"}, "$unset": {"reminder_sent": ""}})
        try:
            r = requests.post(f"{API}/admin/bookings/{bid}/reminder", headers=auth_headers, timeout=30)
            assert r.status_code == 502
            # detail may be JSON with French text or an ingress HTML wrapper — accept both
            try:
                assert "detail" in r.json()
            except Exception:
                assert r.text  # any body OK
        finally:
            db.bookings.update_one({"id": bid}, {"$set": {"status": original_status}})


# --- Reminders batch run ---
class TestRemindersRun:
    def test_run_reminders_idempotent(self, auth_headers, db):
        # Set a delivered@resend.dev confirmed booking to tomorrow (Canary TZ)
        tomorrow = (datetime.now(TZ_CANARY) + timedelta(days=1)).date().isoformat()
        booking = db.bookings.find_one({"email": "delivered@resend.dev"})
        assert booking, "No delivered@resend.dev booking seeded"
        bid = booking["id"]
        orig = {
            "date": booking.get("date"),
            "status": booking.get("status"),
            "reminder_sent": booking.get("reminder_sent"),
            "reminder_sent_at": booking.get("reminder_sent_at"),
            "reminder_spot": booking.get("reminder_spot"),
        }
        db.bookings.update_one(
            {"id": bid},
            {"$set": {"date": tomorrow, "status": "confirmed"},
             "$unset": {"reminder_sent": "", "reminder_sent_at": "", "reminder_spot": ""}},
        )
        try:
            r1 = requests.post(f"{API}/admin/reminders/run", headers=auth_headers, timeout=60)
            assert r1.status_code == 200, r1.text
            d1 = r1.json()
            assert d1["date"] == tomorrow
            assert d1["sent"] >= 1
            r2 = requests.post(f"{API}/admin/reminders/run", headers=auth_headers, timeout=30)
            assert r2.status_code == 200
            d2 = r2.json()
            assert d2["sent"] == 0
        finally:
            restore = {}
            unset = {}
            for k, v in orig.items():
                if v is None:
                    unset[k] = ""
                else:
                    restore[k] = v
            op = {}
            if restore:
                op["$set"] = restore
            if unset:
                op["$unset"] = unset
            if op:
                db.bookings.update_one({"id": bid}, op)

    def test_run_does_not_send_pending_or_cancelled(self, auth_headers, db):
        tomorrow = (datetime.now(TZ_CANARY) + timedelta(days=1)).date().isoformat()
        # Create a temp pending example.com booking for tomorrow
        import uuid as _uuid
        pending_id = str(_uuid.uuid4())
        db.bookings.insert_one({
            "id": pending_id, "name": "TEST Pending", "email": "delivered@resend.dev",
            "phone": "+34600000000", "experience": "discovery", "date": tomorrow,
            "participants": 1, "status": "pending", "lang": "fr",
            "created_at": datetime.now(timezone.utc).isoformat() if False else datetime.utcnow().isoformat(),
            "partner": False, "slot": None, "amount": 145,
        })
        cancelled_id = str(_uuid.uuid4())
        db.bookings.insert_one({
            "id": cancelled_id, "name": "TEST Cancelled", "email": "delivered@resend.dev",
            "phone": "+34600000000", "experience": "discovery", "date": tomorrow,
            "participants": 1, "status": "cancelled", "lang": "fr",
            "created_at": datetime.utcnow().isoformat(),
            "partner": False, "slot": None, "amount": 145,
        })
        try:
            r = requests.post(f"{API}/admin/reminders/run", headers=auth_headers, timeout=60)
            assert r.status_code == 200
            # Verify neither got reminder_sent
            p = db.bookings.find_one({"id": pending_id})
            c = db.bookings.find_one({"id": cancelled_id})
            assert not p.get("reminder_sent")
            assert not c.get("reminder_sent")
        finally:
            db.bookings.delete_one({"id": pending_id})
            db.bookings.delete_one({"id": cancelled_id})


# --- Confirmation email still works (log level) ---
class TestConfirmEmailSlotInclusion:
    def test_patch_confirmed_returns_confirmation_flag(self, auth_headers, db):
        booking = db.bookings.find_one({"email": "delivered@resend.dev"})
        assert booking
        bid = booking["id"]
        orig_status = booking.get("status")
        orig_slot = booking.get("slot")
        # set to pending with slot 1 then confirm
        db.bookings.update_one({"id": bid}, {"$set": {"status": "pending", "slot": 1}})
        try:
            r = requests.patch(f"{API}/admin/bookings/{bid}", headers=auth_headers,
                               json={"status": "confirmed"}, timeout=30)
            assert r.status_code == 200
            d = r.json()
            assert d["status"] == "confirmed"
            assert d.get("confirmation_email_sent") is True
        finally:
            db.bookings.update_one({"id": bid}, {"$set": {"status": orig_status, "slot": orig_slot}})
