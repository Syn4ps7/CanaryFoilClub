"""Backend tests for Canary Foil Club — iteration 3.
Covers: POST /api/auth/change-password, GET /api/admin/weather, GET /api/admin/planning/week.
"""
import os
import subprocess
from datetime import datetime, timezone, timedelta, date
import pytest
import requests


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
NEW_PASSWORD = "Test1234!"


def _login(pw):
    return requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": pw}, timeout=15)


def _restore_admin_password():
    """Restore admin password to 'admin' via direct DB update (bcrypt hash)."""
    script = (
        "import os;from dotenv import load_dotenv;load_dotenv('.env');"
        "from pymongo import MongoClient;from auth import hash_password;"
        "db=MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']];"
        "print(db.users.update_one({'email':'admin'},{'$set':{'password_hash':hash_password('admin')}}).modified_count)"
    )
    r = subprocess.run(["python3", "-c", script], cwd="/app/backend", capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, f"restore failed: {r.stderr}"


@pytest.fixture(scope="session")
def admin_token():
    r = _login(ADMIN_PASSWORD)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- Change password ---
class TestChangePassword:
    def test_no_auth(self):
        r = requests.post(f"{API}/auth/change-password",
                          json={"current_password": "admin", "new_password": "whatever8"}, timeout=15)
        assert r.status_code == 401

    def test_wrong_current(self, auth_headers):
        r = requests.post(f"{API}/auth/change-password", headers=auth_headers,
                          json={"current_password": "wrongpassword", "new_password": "NewPass123"}, timeout=15)
        assert r.status_code == 400
        assert "actuel" in r.json().get("detail", "").lower()

    def test_new_too_short_422(self, auth_headers):
        r = requests.post(f"{API}/auth/change-password", headers=auth_headers,
                          json={"current_password": "admin", "new_password": "short"}, timeout=15)
        # Pydantic validates min_length=8 -> 422
        assert r.status_code == 422

    def test_change_and_login_and_restore(self, auth_headers):
        # Valid change admin -> Test1234!
        r = requests.post(f"{API}/auth/change-password", headers=auth_headers,
                          json={"current_password": "admin", "new_password": NEW_PASSWORD}, timeout=15)
        assert r.status_code == 200, f"change failed: {r.status_code} {r.text}"
        assert r.json() == {"ok": True}

        # Old password fails
        r_old = _login("admin")
        assert r_old.status_code == 401

        # New password works
        r_new = _login(NEW_PASSWORD)
        assert r_new.status_code == 200
        new_token = r_new.json()["token"]

        # Same as current -> 400
        r_same = requests.post(f"{API}/auth/change-password",
                               headers={"Authorization": f"Bearer {new_token}"},
                               json={"current_password": NEW_PASSWORD, "new_password": NEW_PASSWORD}, timeout=15)
        assert r_same.status_code == 400

        # Restore via DB
        _restore_admin_password()
        r_restore = _login("admin")
        assert r_restore.status_code == 200, "admin/admin login failed after restore"


# --- Weather ---
class TestWeather:
    def test_no_auth(self):
        r = requests.get(f"{API}/admin/weather?day=2026-06-01", timeout=20)
        assert r.status_code == 401

    def test_invalid_day(self, auth_headers):
        r = requests.get(f"{API}/admin/weather?day=not-a-date", headers=auth_headers, timeout=20)
        assert r.status_code == 400

    def test_weather_today_shape_and_cache(self, auth_headers):
        today = datetime.now(timezone.utc).date().isoformat()
        r1 = requests.get(f"{API}/admin/weather?day={today}", headers=auth_headers, timeout=30)
        assert r1.status_code == 200, f"{r1.status_code} {r1.text}"
        d = r1.json()
        for k in ("date", "summary", "spot", "hourly", "source", "cached"):
            assert k in d, f"missing {k}"
        assert d["date"] == today
        for k in ("wind_avg", "wind_max", "gust_max", "wind_dir", "wind_dir_label",
                  "wave_avg", "wave_max", "period_avg", "wave_dir", "wave_dir_label", "temp_max"):
            assert k in d["summary"], f"summary missing {k}"
        assert d["spot"]["level"] in {"ideal", "good", "caution", "nogo", "unknown"}
        assert "spot" in d["spot"] and "reason" in d["spot"]
        # hourly only 08:00 → 20:00
        assert isinstance(d["hourly"], list) and len(d["hourly"]) >= 1
        for h in d["hourly"]:
            hh = int(h["time"][:2])
            assert 8 <= hh <= 20, f"hour {hh} outside 8-20"
            for k in ("time", "wind", "gust", "wind_dir", "temp", "wave", "period", "wave_dir"):
                assert k in h

        # Second call same day -> cached
        r2 = requests.get(f"{API}/admin/weather?day={today}", headers=auth_headers, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["cached"] is True

    def test_weather_past_date_acceptable(self, auth_headers):
        """A very old date may return 502/504 or nulls — acceptable, just report."""
        r = requests.get(f"{API}/admin/weather?day=2020-01-01", headers=auth_headers, timeout=30)
        # Just make sure it doesn't 500. 200 or 502/504 is acceptable.
        assert r.status_code in (200, 400, 502, 504), f"unexpected {r.status_code} {r.text[:200]}"


# --- Week planning ---
class TestWeekPlanning:
    def test_no_auth(self):
        r = requests.get(f"{API}/admin/planning/week?start=2026-01-05", timeout=15)
        assert r.status_code == 401

    def test_week_normalizes_to_monday(self, auth_headers):
        # 2026-01-07 is a Wednesday -> should normalize to Monday 2026-01-05
        r = requests.get(f"{API}/admin/planning/week?start=2026-01-07", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["start"] == "2026-01-05"
        assert d["end"] == "2026-01-11"
        assert isinstance(d["days"], list) and len(d["days"]) == 7
        # Verify dates are contiguous
        for i, day in enumerate(d["days"]):
            expected = (date(2026, 1, 5) + timedelta(days=i)).isoformat()
            assert day["date"] == expected
            for k in ("used", "pending", "capacity", "occupancy", "sessions", "pending_count", "revenue", "unassigned"):
                assert k in day, f"missing {k} in day {day['date']}"
            assert isinstance(day["capacity"], int) and day["capacity"] > 0
            assert day["used"] <= day["capacity"]
            assert 0 <= day["occupancy"] <= 100

    def test_week_capacity_matches_settings(self, auth_headers):
        s = requests.get(f"{API}/admin/settings", headers=auth_headers, timeout=15).json()
        expected_cap = s["boards"] * s["slots_per_day"]
        r = requests.get(f"{API}/admin/planning/week?start=2026-06-01", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        for day in r.json()["days"]:
            assert day["capacity"] == expected_cap

    def test_week_default_no_start(self, auth_headers):
        r = requests.get(f"{API}/admin/planning/week", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        # start must be a Monday
        parsed = date.fromisoformat(d["start"])
        assert parsed.weekday() == 0
        assert len(d["days"]) == 7
