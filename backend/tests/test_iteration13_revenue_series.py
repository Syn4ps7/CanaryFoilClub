"""Iteration 13: /api/admin/stats/revenue-series"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback: read from frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin", "password": "admin"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_no_token_401():
    r = requests.get(f"{BASE_URL}/api/admin/stats/revenue-series")
    assert r.status_code in (401, 403)


def test_default_30(headers):
    r = requests.get(f"{BASE_URL}/api/admin/stats/revenue-series", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["days"] == 30
    assert len(data["series"]) == 30
    for item in data["series"]:
        for k in ("date", "revenue", "bookings", "cumulative"):
            assert k in item
    # cumulative monotonic
    cums = [d["cumulative"] for d in data["series"]]
    assert all(cums[i] <= cums[i + 1] + 1e-6 for i in range(len(cums) - 1))
    # last cumulative == total
    assert abs(cums[-1] - data["total"]) < 0.01
    # total == sum(revenue)
    assert abs(sum(d["revenue"] for d in data["series"]) - data["total"]) < 0.01
    # consecutive dates ending today (UTC)
    from datetime import datetime, timezone, date, timedelta
    today = datetime.now(timezone.utc).date()
    dates = [date.fromisoformat(d["date"]) for d in data["series"]]
    assert dates[-1] == today
    for i in range(1, len(dates)):
        assert (dates[i] - dates[i - 1]).days == 1


def test_days_90(headers):
    r = requests.get(f"{BASE_URL}/api/admin/stats/revenue-series", headers=headers, params={"days": 90})
    assert r.status_code == 200
    data = r.json()
    assert data["days"] == 90
    assert len(data["series"]) == 90


def test_days_5_422(headers):
    r = requests.get(f"{BASE_URL}/api/admin/stats/revenue-series", headers=headers, params={"days": 5})
    assert r.status_code == 422


def test_days_400_422(headers):
    r = requests.get(f"{BASE_URL}/api/admin/stats/revenue-series", headers=headers, params={"days": 400})
    assert r.status_code == 422


def test_cross_check_with_stats(headers):
    r_series = requests.get(f"{BASE_URL}/api/admin/stats/revenue-series", headers=headers, params={"days": 30})
    r_stats = requests.get(f"{BASE_URL}/api/admin/stats", headers=headers)
    assert r_series.status_code == 200 and r_stats.status_code == 200
    series = r_series.json()
    stats = r_stats.json()
    # total over 30 days <= stats.revenue.total
    assert series["total"] <= stats["revenue"]["total"] + 0.01
    # sum of today's series entry revenue == stats.revenue.today
    today_entry = series["series"][-1]
    assert abs(today_entry["revenue"] - stats["revenue"]["today"]) < 0.01
