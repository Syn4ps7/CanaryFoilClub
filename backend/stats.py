from datetime import datetime, timezone, date
from calendar import monthrange

BOARDS = 3
SLOTS_PER_DAY = 4
DAILY_CAPACITY = BOARDS * SLOTS_PER_DAY
COMMISSION_RATE = 0.20
REVENUE_STATUSES = {"confirmed", "completed"}

PRICES = {"discovery": 145, "duo": 280, "drone": 50, "corporate": 890, "testdrive": 0}
CATEGORY = {"discovery": "b2c", "duo": "b2c", "testdrive": "b2c", "corporate": "corporate", "drone": "drone"}


def price_of(b: dict) -> float:
    exp, n = b.get("experience", "discovery"), int(b.get("participants", 1) or 1)
    if exp == "discovery":
        return PRICES["discovery"] * n
    if exp == "drone":
        return PRICES["drone"] * n
    return float(PRICES.get(exp, 0))


def board_slots_of(b: dict) -> int:
    exp, n = b.get("experience"), int(b.get("participants", 1) or 1)
    if exp == "discovery":
        return min(n, BOARDS)
    if exp == "duo":
        return 2
    if exp == "testdrive":
        return 1
    if exp == "corporate":
        return BOARDS * 3
    return 0


def _session_date(b: dict):
    try:
        return date.fromisoformat(str(b.get("date"))[:10])
    except ValueError:
        return None


def compute_stats(bookings: list[dict]) -> dict:
    today = datetime.now(timezone.utc).date()
    month_days = monthrange(today.year, today.month)[1]
    revenue = {"today": 0.0, "month": 0.0, "total": 0.0}
    by_offer = {"b2c": 0.0, "corporate": 0.0, "drone": 0.0}
    commissions = 0.0
    sessions = {"total": 0, "today": 0, "month": 0}
    slots = {"today": 0, "month": 0}
    status_counts = {}

    for b in bookings:
        status_counts[b.get("status", "pending")] = status_counts.get(b.get("status", "pending"), 0) + 1
        if b.get("status") not in REVENUE_STATUSES:
            continue
        amount = price_of(b)
        d = _session_date(b)
        is_today = d == today
        is_month = d is not None and d.year == today.year and d.month == today.month

        revenue["total"] += amount
        sessions["total"] += 1
        by_offer[CATEGORY.get(b.get("experience"), "b2c")] += amount
        if b.get("partner"):
            commissions += amount * COMMISSION_RATE
        if is_today:
            revenue["today"] += amount
            sessions["today"] += 1
            slots["today"] += board_slots_of(b)
        if is_month:
            revenue["month"] += amount
            sessions["month"] += 1
            slots["month"] += board_slots_of(b)

    return {
        "revenue": revenue,
        "sessions": sessions,
        "occupancy": {
            "today": round(min(slots["today"] / DAILY_CAPACITY, 1) * 100, 1),
            "month": round(min(slots["month"] / (DAILY_CAPACITY * month_days), 1) * 100, 1),
            "boards": BOARDS,
            "slots_per_day": SLOTS_PER_DAY,
        },
        "by_offer": by_offer,
        "commissions": round(commissions, 2),
        "commission_rate": COMMISSION_RATE,
        "status_counts": status_counts,
        "pending": status_counts.get("pending", 0),
    }
