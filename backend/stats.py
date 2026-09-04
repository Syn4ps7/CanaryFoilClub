from datetime import datetime, timezone, date
from calendar import monthrange

MAX_BOARDS = 6
MAX_SLOTS = 6
DEFAULT_SETTINGS = {"boards": 3, "slots_per_day": 6}
COMMISSION_RATE = 0.20
REVENUE_STATUSES = {"confirmed", "completed"}
CORPORATE_SLOTS = 3

PRICES = {"discovery": 145, "duo": 280, "drone": 50, "corporate": 890, "testdrive": 0}
CATEGORY = {"discovery": "b2c", "duo": "b2c", "testdrive": "b2c", "corporate": "corporate", "drone": "drone"}


def price_of(b: dict) -> float:
    exp, n = b.get("experience", "discovery"), int(b.get("participants", 1) or 1)
    if exp == "discovery":
        return PRICES["discovery"] * n
    if exp == "drone":
        return PRICES["drone"] * n
    return float(PRICES.get(exp, 0))


def boards_of(b: dict, boards: int) -> int:
    exp, n = b.get("experience"), int(b.get("participants", 1) or 1)
    if exp == "discovery":
        return min(n, boards)
    if exp == "duo":
        return min(2, boards)
    if exp == "testdrive":
        return 1
    if exp == "corporate":
        return boards
    return 0


def slots_of(b: dict) -> int:
    return CORPORATE_SLOTS if b.get("experience") == "corporate" else (0 if b.get("experience") == "drone" else 1)


def board_slots_of(b: dict, boards: int) -> int:
    return boards_of(b, boards) * slots_of(b)


def session_date(b: dict):
    try:
        return date.fromisoformat(str(b.get("date"))[:10])
    except ValueError:
        return None


def compute_stats(bookings: list[dict], settings: dict) -> dict:
    boards, slots_per_day = settings["boards"], settings["slots_per_day"]
    capacity = boards * slots_per_day
    today = datetime.now(timezone.utc).date()
    month_days = monthrange(today.year, today.month)[1]
    revenue = {"today": 0.0, "month": 0.0, "total": 0.0}
    by_offer = {"b2c": 0.0, "corporate": 0.0, "drone": 0.0}
    commissions = 0.0
    sessions = {"total": 0, "today": 0, "month": 0}
    used = {"today": 0, "month": 0}
    status_counts = {}

    for b in bookings:
        st = b.get("status", "pending")
        status_counts[st] = status_counts.get(st, 0) + 1
        if st not in REVENUE_STATUSES:
            continue
        amount = price_of(b)
        d = session_date(b)
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
            used["today"] += board_slots_of(b, boards)
        if is_month:
            revenue["month"] += amount
            sessions["month"] += 1
            used["month"] += board_slots_of(b, boards)

    return {
        "revenue": revenue,
        "sessions": sessions,
        "occupancy": {
            "today": round(min(used["today"] / capacity, 1) * 100, 1),
            "month": round(min(used["month"] / (capacity * month_days), 1) * 100, 1),
            "used_today": used["today"],
            "capacity": capacity,
            "boards": boards,
            "slots_per_day": slots_per_day,
        },
        "by_offer": by_offer,
        "commissions": round(commissions, 2),
        "commission_rate": COMMISSION_RATE,
        "status_counts": status_counts,
        "pending": status_counts.get("pending", 0),
    }


def compute_week(bookings: list[dict], start: date, settings: dict) -> list[dict]:
    from datetime import timedelta
    boards, slots_per_day = settings["boards"], settings["slots_per_day"]
    capacity = boards * slots_per_day
    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        day_b = [b for b in bookings if session_date(b) == d and b.get("status") != "cancelled"]
        used = sum(board_slots_of(b, boards) for b in day_b if b.get("status") in REVENUE_STATUSES)
        pending_slots = sum(board_slots_of(b, boards) for b in day_b if b.get("status") == "pending")
        days.append({
            "date": d.isoformat(),
            "used": min(used, capacity),
            "pending": min(pending_slots, capacity - min(used, capacity)),
            "capacity": capacity,
            "occupancy": round(min(used / capacity, 1) * 100) if capacity else 0,
            "sessions": sum(1 for b in day_b if b.get("status") in REVENUE_STATUSES),
            "pending_count": sum(1 for b in day_b if b.get("status") == "pending"),
            "revenue": sum(price_of(b) for b in day_b if b.get("status") in REVENUE_STATUSES),
            "unassigned": sum(1 for b in day_b if not b.get("slot") and boards_of(b, boards) > 0),
        })
    return days


def compute_planning(bookings: list[dict], day: date, settings: dict) -> dict:
    boards, slots_per_day = settings["boards"], settings["slots_per_day"]
    grid = [{"slot": i, "bookings": [], "used": 0} for i in range(1, slots_per_day + 1)]
    unassigned = []
    for b in bookings:
        if session_date(b) != day or b.get("status") == "cancelled":
            continue
        need = boards_of(b, boards)
        slot = b.get("slot")
        if not slot or slot > slots_per_day or need == 0:
            (unassigned if need else []).append(b)
            continue
        for i in range(slot, min(slot + slots_of(b), slots_per_day + 1)):
            grid[i - 1]["bookings"].append(b)
            grid[i - 1]["used"] += need
    for g in grid:
        g["free"] = max(boards - g["used"], 0)
        g["overbooked"] = g["used"] > boards
    return {
        "date": day.isoformat(),
        "boards": boards,
        "slots_per_day": slots_per_day,
        "slots": grid,
        "unassigned": unassigned,
        "used": sum(min(g["used"], boards) for g in grid),
        "capacity": boards * slots_per_day,
    }
