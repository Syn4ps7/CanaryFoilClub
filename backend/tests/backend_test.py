"""Backend tests for Canary Foil Club — iteration 2 (admin/admin, settings, bookings filter, CSV, planning, PATCH+email)."""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta

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
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin"
ADMIN_PASSWORD = "admin"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- Auth ---
class TestAuth:
    def test_login_admin_admin(self):
        r = requests.post(f"{API}/auth/login", json={"email": "admin", "password": "admin"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == "admin"
        assert d["role"] == "admin"
        assert isinstance(d["token"], str) and len(d["token"]) > 20

    def test_login_old_email_fails(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "admin@canaryfoilclub.com", "password": "Foil!Club2026"}, timeout=15)
        assert r.status_code == 401

    def test_login_wrong_password(self):
        # Use unique identifier to avoid locking the real admin
        r = requests.post(f"{API}/auth/login",
                          json={"email": f"nobody-{uuid.uuid4().hex[:6]}@test.com", "password": "wrong"}, timeout=15)
        assert r.status_code == 401


# --- Settings ---
class TestSettings:
    def test_settings_get_default(self, auth_headers):
        r = requests.get(f"{API}/admin/settings", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "boards" in d and "slots_per_day" in d
        assert 1 <= d["boards"] <= 6
        assert 1 <= d["slots_per_day"] <= 6

    def test_settings_no_auth(self):
        r = requests.get(f"{API}/admin/settings", timeout=15)
        assert r.status_code == 401

    def test_settings_put_max_ok(self, auth_headers):
        r = requests.put(f"{API}/admin/settings", json={"boards": 6, "slots_per_day": 6},
                         headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["boards"] == 6 and d["slots_per_day"] == 6
        # Verify persistence
        r2 = requests.get(f"{API}/admin/settings", headers=auth_headers, timeout=15)
        assert r2.json()["boards"] == 6 and r2.json()["slots_per_day"] == 6
        # Stats occupancy uses new capacity
        rs = requests.get(f"{API}/admin/stats", headers=auth_headers, timeout=15)
        occ = rs.json()["occupancy"]
        assert occ["capacity"] == 36
        assert occ["boards"] == 6 and occ["slots_per_day"] == 6
        # occupancy.today == used_today/capacity*100 rounded 1 decimal
        expected = round(min(occ["used_today"] / 36, 1) * 100, 1)
        assert occ["today"] == expected

    def test_settings_put_over_max_boards(self, auth_headers):
        r = requests.put(f"{API}/admin/settings", json={"boards": 7, "slots_per_day": 6},
                         headers=auth_headers, timeout=15)
        assert r.status_code == 422

    def test_settings_put_over_max_slots(self, auth_headers):
        r = requests.put(f"{API}/admin/settings", json={"boards": 3, "slots_per_day": 7},
                         headers=auth_headers, timeout=15)
        assert r.status_code == 422

    def test_settings_restore(self, auth_headers):
        r = requests.put(f"{API}/admin/settings", json={"boards": 3, "slots_per_day": 6},
                         headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["boards"] == 3 and r.json()["slots_per_day"] == 6


# --- Admin bookings list w/ filters ---
class TestAdminBookings:
    def test_no_auth(self):
        r = requests.get(f"{API}/admin/bookings", timeout=15)
        assert r.status_code == 401

    def test_list_all(self, auth_headers):
        r = requests.get(f"{API}/admin/bookings", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # Sorted by date desc
        dates = [b["date"] for b in data if b.get("date")]
        assert dates == sorted(dates, reverse=True)

    def test_filter_status(self, auth_headers):
        r = requests.get(f"{API}/admin/bookings?status=confirmed", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        for b in r.json():
            assert b["status"] == "confirmed"

    def test_filter_q_by_name(self, auth_headers):
        # First fetch a booking to use its name substring
        all_r = requests.get(f"{API}/admin/bookings", headers=auth_headers, timeout=15).json()
        if not all_r:
            pytest.skip("no bookings")
        target = all_r[0]
        q = target["name"][:3].upper()  # case-insensitive
        r = requests.get(f"{API}/admin/bookings?q={q}", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert any(target["name"] == b["name"] for b in r.json())
        for b in r.json():
            # match against name/email/phone/hotel/partner_name
            hay = " ".join(str(b.get(k) or "") for k in ("name", "email", "phone", "hotel", "partner_name")).lower()
            assert q.lower() in hay

    def test_filter_date_range(self, auth_headers):
        r = requests.get(f"{API}/admin/bookings?date_from=2026-01-01&date_to=2026-12-31",
                         headers=auth_headers, timeout=15)
        assert r.status_code == 200
        for b in r.json():
            assert "2026-01-01" <= b["date"][:10] <= "2026-12-31"


# --- CSV export ---
class TestCSVExport:
    def test_no_auth(self):
        r = requests.get(f"{API}/admin/bookings/export.csv", timeout=15)
        assert r.status_code == 401

    def test_export_headers_and_bom(self, auth_headers):
        r = requests.get(f"{API}/admin/bookings/export.csv", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "").lower()
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower()
        body = r.content.decode("utf-8")
        assert body.startswith("\ufeff"), "CSV must start with BOM"
        first_line = body.split("\n", 1)[0]
        assert first_line.startswith("\ufeffid;date_session;creneau;statut;")

    def test_export_status_filter(self, auth_headers):
        r = requests.get(f"{API}/admin/bookings/export.csv?status=completed",
                         headers=auth_headers, timeout=30)
        assert r.status_code == 200
        body = r.content.decode("utf-8-sig")
        lines = [ln for ln in body.strip().split("\n") if ln]
        # Header + rows; every data row should have statut=completed (col idx 3)
        for line in lines[1:]:
            cols = line.split(";")
            assert cols[3] == "completed", f"non-completed row present: {line}"

    def test_export_commission_only_partner_confirmed(self, auth_headers):
        r = requests.get(f"{API}/admin/bookings/export.csv", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        body = r.content.decode("utf-8-sig")
        lines = [ln for ln in body.strip().split("\n") if ln]
        for line in lines[1:]:
            cols = line.split(";")
            # cols: id;date;creneau;statut;client;email;telephone;experience;participants;montant;partenaire;partner_name;commission;...
            statut, partenaire, commission = cols[3], cols[10], cols[12]
            eligible = partenaire == "oui" and statut in ("confirmed", "completed")
            if not eligible:
                assert commission == "0,00", f"non-eligible row has commission {commission}: {line}"


# --- Planning ---
class TestPlanning:
    def test_planning_shape(self, auth_headers):
        today = datetime.now(timezone.utc).date().isoformat()
        r = requests.get(f"{API}/admin/planning?day={today}", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("date", "boards", "slots_per_day", "slots", "unassigned", "used", "capacity"):
            assert k in d, f"missing {k}"
        assert d["date"] == today
        assert d["capacity"] == d["boards"] * d["slots_per_day"]
        assert len(d["slots"]) == d["slots_per_day"]
        for s in d["slots"]:
            for kk in ("slot", "bookings", "used", "free", "overbooked"):
                assert kk in s

    def test_planning_invalid_day(self, auth_headers):
        r = requests.get(f"{API}/admin/planning?day=not-a-date", headers=auth_headers, timeout=15)
        assert r.status_code == 400

    def test_planning_no_auth(self):
        r = requests.get(f"{API}/admin/planning?day=2026-06-01", timeout=15)
        assert r.status_code == 401


# --- PATCH booking + email confirmation ---
class TestPatchBooking:
    def test_patch_no_auth(self):
        r = requests.patch(f"{API}/admin/bookings/anything", json={"status": "confirmed"}, timeout=15)
        assert r.status_code == 401

    def test_patch_slot_invalid_high(self, auth_headers):
        # find any booking
        bs = requests.get(f"{API}/admin/bookings", headers=auth_headers, timeout=15).json()
        if not bs:
            pytest.skip("no bookings")
        r = requests.patch(f"{API}/admin/bookings/{bs[0]['id']}", json={"slot": 7},
                           headers=auth_headers, timeout=15)
        assert r.status_code == 422

    def test_patch_slot_assign_then_unassign(self, auth_headers):
        bs = requests.get(f"{API}/admin/bookings", headers=auth_headers, timeout=15).json()
        if not bs:
            pytest.skip("no bookings")
        bid = bs[0]["id"]
        orig_slot = bs[0].get("slot")
        # assign slot 2
        r = requests.patch(f"{API}/admin/bookings/{bid}", json={"slot": 2},
                           headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["slot"] == 2
        # unassign with slot 0 -> null
        r = requests.patch(f"{API}/admin/bookings/{bid}", json={"slot": 0},
                           headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["slot"] is None
        # restore
        if orig_slot:
            requests.patch(f"{API}/admin/bookings/{bid}", json={"slot": orig_slot},
                           headers=auth_headers, timeout=15)

    def test_patch_status_confirmed_sends_email(self, auth_headers):
        # Find a Laura Gomez or delivered@resend.dev booking
        bs = requests.get(f"{API}/admin/bookings", headers=auth_headers, timeout=15).json()
        target = next((b for b in bs if b.get("email") == "delivered@resend.dev"), None)
        if not target:
            pytest.skip("no delivered@resend.dev booking seeded")
        bid = target["id"]
        orig_status = target["status"]
        # First, ensure it is NOT confirmed
        if orig_status == "confirmed":
            requests.patch(f"{API}/admin/bookings/{bid}", json={"status": "pending"},
                           headers=auth_headers, timeout=15)
            time.sleep(0.5)
        # Now confirm - should trigger email
        r = requests.patch(f"{API}/admin/bookings/{bid}", json={"status": "confirmed"},
                           headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"
        time.sleep(2)  # let email send complete
        # Verify via backend log (spec says "check log OR via GET"; API strips extra fields from Booking model)
        try:
            with open("/var/log/supervisor/backend.err.log") as f:
                log = f.read()
        except Exception:
            log = ""
        assert "Client confirmed-email sent" in log and "delivered@resend.dev" in log, \
            "'Client confirmed-email sent' log entry to delivered@resend.dev not found"

        # Second call: confirmed->confirmed should NOT re-trigger. We can't easily verify by log here,
        # but the endpoint must still 200 without error.
        r2 = requests.patch(f"{API}/admin/bookings/{bid}", json={"status": "confirmed"},
                            headers=auth_headers, timeout=15)
        assert r2.status_code == 200

        # restore
        requests.patch(f"{API}/admin/bookings/{bid}", json={"status": orig_status},
                       headers=auth_headers, timeout=15)
