import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from emailer import notify_reminder
from weather import get_weather, SPOT_ADDRESS, conditions_label
from stats import slot_label

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Atlantic/Canary")
REMINDER_HOUR = 17
CHECK_EVERY = 15 * 60


async def meeting_point(db, day: str) -> dict:
    override = await db.day_plans.find_one({"date": day}, {"_id": 0})
    weather, summary = None, {}
    try:
        weather = await get_weather(day)
        summary = weather["summary"]
    except Exception as e:
        logger.warning(f"Weather unavailable for {day}: {e}")
    if override and override.get("spot"):
        return {"date": day, "spot": override["spot"], "address": override.get("address") or SPOT_ADDRESS.get(override["spot"], ""),
                "source": "override", "summary": summary, "weather_spot": weather["spot"] if weather else None}
    if weather:
        spot = weather["spot"]["spot"]
        return {"date": day, "spot": spot, "address": SPOT_ADDRESS.get(spot, ""), "source": "weather", "summary": summary, "weather_spot": weather["spot"]}
    return {"date": day, "spot": "Playa del Duque / Fañabé", "address": SPOT_ADDRESS["Playa del Duque / Fañabé"], "source": "default", "summary": {}, "weather_spot": None}


async def send_reminder(db, booking_model, booking: dict, settings: dict, force: bool = False) -> bool:
    mp = await meeting_point(db, str(booking["date"])[:10])
    b = booking_model(**booking)
    conditions = conditions_label(mp["summary"], b.lang) if mp["summary"] else ""
    sent = await notify_reminder(b, slot_label(settings, booking.get("slot")), mp["spot"], mp["address"], conditions)
    await db.bookings.update_one(
        {"id": booking["id"]},
        {"$set": {"reminder_sent": sent, "reminder_sent_at": datetime.now(TZ).isoformat(), "reminder_spot": mp["spot"], "reminder_forced": force}},
    )
    return sent


async def run_reminders(db, booking_model, get_settings, normalize) -> dict:
    tomorrow = (datetime.now(TZ) + timedelta(days=1)).date().isoformat()
    settings = await get_settings()
    cursor = db.bookings.find(
        {"date": {"$regex": f"^{tomorrow}"}, "status": "confirmed", "reminder_sent": {"$ne": True}},
        {"_id": 0},
    )
    results = {"date": tomorrow, "sent": 0, "failed": 0}
    async for raw in cursor:
        ok = await send_reminder(db, booking_model, normalize(raw), settings)
        results["sent" if ok else "failed"] += 1
    if results["sent"] or results["failed"]:
        logger.info(f"Reminders for {tomorrow}: {results}")
    return results


async def reminder_loop(db, booking_model, get_settings, normalize):
    while True:
        try:
            if datetime.now(TZ).hour >= REMINDER_HOUR:
                await run_reminders(db, booking_model, get_settings, normalize)
        except Exception as e:
            logger.error(f"Reminder loop error: {e}")
        await asyncio.sleep(CHECK_EVERY)


async def periodic(name: str, fn, interval: int = CHECK_EVERY):
    while True:
        try:
            await fn()
        except Exception as e:
            logger.error(f"{name} loop error: {e}")
        await asyncio.sleep(interval)
