import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from emailer import notify_review_request, send_weekly_report
from stats import compute_week, price_of, CATEGORY, COMMISSION_RATE, REVENUE_STATUSES

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Atlantic/Canary")
REVIEW_HOUR = 9
REPORT_HOUR = 8
OFFER_LABELS = {"b2c": "B2C classique", "corporate": "Pack B2B Corporate Sunset", "drone": "Options Drone"}


def review_url(token: str) -> str:
    return f"{os.environ['SITE_URL'].rstrip('/')}/avis/{token}"


async def ensure_review_token(db, booking: dict) -> str:
    if booking.get("review_token"):
        return booking["review_token"]
    token = secrets.token_urlsafe(24)
    await db.bookings.update_one({"id": booking["id"]}, {"$set": {"review_token": token}})
    return token


async def send_review_request(db, booking_model, booking: dict, force: bool = False) -> bool:
    token = await ensure_review_token(db, booking)
    sent = await notify_review_request(booking_model(**booking), review_url(token))
    await db.bookings.update_one(
        {"id": booking["id"]},
        {"$set": {"review_request_sent": sent, "review_request_sent_at": datetime.now(TZ).isoformat(), "review_request_forced": force}},
    )
    return sent


async def run_review_requests(db, booking_model, normalize) -> dict:
    yesterday = (datetime.now(TZ) - timedelta(days=1)).date().isoformat()
    cursor = db.bookings.find(
        {"date": {"$regex": f"^{yesterday}"}, "status": {"$in": list(REVENUE_STATUSES)}, "review_request_sent": {"$ne": True}},
        {"_id": 0},
    )
    results = {"date": yesterday, "sent": 0, "failed": 0}
    async for raw in cursor:
        ok = await send_review_request(db, booking_model, normalize(raw))
        results["sent" if ok else "failed"] += 1
    if results["sent"] or results["failed"]:
        logger.info(f"Review requests for {yesterday}: {results}")
    return results


async def build_weekly_report(db, settings: dict, week_start=None) -> dict:
    today = datetime.now(TZ).date()
    start = week_start or (today - timedelta(days=today.weekday() + 7))
    end = start + timedelta(days=6)
    next_start, next_end = end + timedelta(days=1), end + timedelta(days=7)
    raw = await db.bookings.find({"date": {"$gte": start.isoformat(), "$lte": next_end.isoformat() + "~"}}, {"_id": 0}).to_list(5000)
    for b in raw:
        b.setdefault("partner", False)
    days = compute_week(raw, start, settings)
    next_days = compute_week(raw, next_start, settings)
    fmt = lambda d: datetime.fromisoformat(d["date"]).strftime("%a %d %b").replace(".", "")
    for d in days + next_days:
        d["label"] = fmt(d)
        d["pending"] = d["pending_count"]
    week_b = [b for b in raw if start.isoformat() <= str(b.get("date"))[:10] <= end.isoformat() and b.get("status") in REVENUE_STATUSES]
    by_offer = {v: 0.0 for v in OFFER_LABELS.values()}
    for b in week_b:
        by_offer[OFFER_LABELS[CATEGORY.get(b.get("experience"), "b2c")]] += price_of(b)
    pending_total = await db.bookings.count_documents({"status": "pending"})
    reviews = await db.reviews.find({"created_at": {"$gte": start.isoformat()}}, {"_id": 0, "rating": 1}).to_list(1000)
    capacity = sum(d["capacity"] for d in days) or 1
    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "week_label": f"{start.strftime('%d/%m')} au {end.strftime('%d/%m/%Y')}",
        "revenue": sum(d["revenue"] for d in days),
        "sessions": sum(d["sessions"] for d in days),
        "occupancy": round(sum(d["used"] for d in days) / capacity * 100),
        "commissions": round(sum(price_of(b) * COMMISSION_RATE for b in week_b if b.get("partner")), 2),
        "empty_days": sum(1 for d in days if d["sessions"] == 0),
        "pending_total": pending_total,
        "by_offer": by_offer,
        "days": days,
        "next_days": next_days,
        "reviews": len(reviews),
        "avg_rating": round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else None,
    }


async def run_weekly_report(db, get_settings, force: bool = False, to: str | None = None) -> dict:
    now = datetime.now(TZ)
    report = await build_weekly_report(db, await get_settings())
    key = report["week_start"]
    if not force:
        if now.weekday() != 0 or now.hour < REPORT_HOUR:
            return {"sent": False, "reason": "not_monday_morning", "week_start": key}
        if await db.weekly_reports.find_one({"week_start": key, "sent": True}):
            return {"sent": False, "reason": "already_sent", "week_start": key}
    sent = await send_weekly_report(report, to=to)
    if not to:
        await db.weekly_reports.update_one(
            {"week_start": key},
            {"$set": {"week_start": key, "sent": sent, "sent_at": now.isoformat(), "revenue": report["revenue"], "sessions": report["sessions"]}},
            upsert=True,
        )
    return {"sent": sent, "week_start": key, "revenue": report["revenue"], "sessions": report["sessions"], "to": to}
