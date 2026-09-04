from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import io
import csv
import logging
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
import asyncio
import re
from datetime import datetime, timezone, date, timedelta
from emailer import notify_owner, notify_client, notify_confirmed
from auth import login as auth_login, seed_admin, get_current_admin_factory, change_password
from stats import compute_stats, compute_planning, compute_week, price_of, slot_label, DEFAULT_SETTINGS, DEFAULT_SLOT_TIMES, MAX_BOARDS, MAX_SLOTS
from weather import get_weather, SPOT_ADDRESS
from reminders import meeting_point, send_reminder, run_reminders, reminder_loop, periodic, REMINDER_HOUR, TZ as CANARY_TZ
from engagement import send_review_request, run_review_requests, build_weekly_report, run_weekly_report, REVIEW_HOUR
from vouchers import gen_code, voucher_value, voucher_state, find_voucher, redeem_voucher, mark_paid_fields, VOUCHER_EXPERIENCES
from emailer import notify_voucher_buyer, notify_owner_voucher
from voucher_pdf import build_voucher_pdf
import secrets
from fastapi.responses import Response

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")
require_admin = get_current_admin_factory(db)

EXPERIENCES = {"discovery", "duo", "drone", "corporate", "testdrive"}
STATUSES = {"pending", "confirmed", "completed", "cancelled"}


class BookingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=30)
    experience: str
    date: str = Field(min_length=4, max_length=40)
    participants: int = Field(ge=1, le=12)
    hotel: Optional[str] = None
    notes: Optional[str] = None
    partner: bool = False
    partner_name: Optional[str] = Field(default=None, max_length=120)
    voucher_code: Optional[str] = Field(default=None, max_length=20)
    lang: str = "fr"


class Booking(BookingCreate):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    amount: float = 0
    discount: float = 0
    slot: Optional[int] = None
    confirmation_email_sent: Optional[bool] = None
    reminder_sent: Optional[bool] = None
    reminder_sent_at: Optional[str] = None
    reminder_spot: Optional[str] = None
    review_request_sent: Optional[bool] = None
    review_request_sent_at: Optional[str] = None
    review_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewInput(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=800)
    display_name: Optional[str] = Field(default=None, max_length=60)


class ReviewUpdate(BaseModel):
    approved: Optional[bool] = None
    featured: Optional[bool] = None
    reply: Optional[str] = Field(default=None, max_length=600)


class Review(BaseModel):
    id: str
    booking_id: str
    name: str
    rating: int
    comment: str
    lang: str
    experience: str
    date: str
    approved: bool = False
    featured: bool = False
    reply: Optional[str] = None
    replied_at: Optional[str] = None
    created_at: str


class VoucherCreate(BaseModel):
    buyer_name: str = Field(min_length=2, max_length=120)
    buyer_email: EmailStr
    recipient_name: str = Field(min_length=2, max_length=120)
    message: Optional[str] = Field(default=None, max_length=300)
    experience: str = "discovery"
    participants: int = Field(default=1, ge=1, le=3)
    lang: str = "fr"


class Voucher(VoucherCreate):
    model_config = ConfigDict(extra="ignore")

    id: str
    code: str
    value: float
    status: str = "pending"
    created_at: str
    paid_at: Optional[str] = None
    expires_at: Optional[str] = None
    redeemed_at: Optional[str] = None
    redeemed_booking_id: Optional[str] = None
    email_sent: Optional[bool] = None
    download_token: Optional[str] = None


class VoucherUpdate(BaseModel):
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LoginInput(BaseModel):
    email: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    partner: Optional[bool] = None
    partner_name: Optional[str] = Field(default=None, max_length=120)
    slot: Optional[int] = Field(default=None, ge=0, le=MAX_SLOTS)


class SettingsInput(BaseModel):
    boards: int = Field(ge=1, le=MAX_BOARDS)
    slots_per_day: int = Field(ge=1, le=MAX_SLOTS)
    slot_times: Optional[List[str]] = None


class MeetingPointInput(BaseModel):
    date: str = Field(min_length=10, max_length=10)
    spot: Optional[str] = Field(default=None, max_length=120)
    address: Optional[str] = Field(default=None, max_length=300)


TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _fit_slot_times(times: Optional[List[str]], n: int) -> List[str]:
    times = [t for t in (times or []) if TIME_RE.match(t)][:n] or DEFAULT_SLOT_TIMES[:n]
    while len(times) < n:
        h, m = map(int, times[-1].split(":"))
        total = min(h * 60 + m + 90, 23 * 60 + 30)
        times.append(f"{total // 60:02d}:{total % 60:02d}")
    return times


class PasswordInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


def _parse_day(day: Optional[str]) -> date:
    try:
        return date.fromisoformat(day) if day else datetime.now(timezone.utc).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Date invalide (YYYY-MM-DD)")


def _normalize(b: dict) -> dict:
    if isinstance(b.get('created_at'), str):
        b['created_at'] = datetime.fromisoformat(b['created_at'])
    b.setdefault('partner', False)
    b.setdefault('slot', None)
    b['amount'] = price_of(b)
    return b


async def get_settings() -> dict:
    doc = await db.settings.find_one({"key": "config"}, {"_id": 0, "key": 0})
    s = {**DEFAULT_SETTINGS, **(doc or {})}
    s["slot_times"] = _fit_slot_times(s.get("slot_times"), s["slots_per_day"])
    return s


def _booking_filter(q: Optional[str], status: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> dict:
    f = {}
    if q:
        rx = {"$regex": q.strip(), "$options": "i"}
        f["$or"] = [{"name": rx}, {"email": rx}, {"phone": rx}, {"hotel": rx}, {"partner_name": rx}]
    if status and status in STATUSES:
        f["status"] = status
    if date_from or date_to:
        f["date"] = {}
        if date_from:
            f["date"]["$gte"] = date_from
        if date_to:
            f["date"]["$lte"] = date_to
    return f


@api_router.get("/")
async def root():
    return {"message": "Canary Foil Club API"}


@api_router.post("/booking", response_model=Booking)
async def create_booking(input: BookingCreate):
    if input.experience not in EXPERIENCES:
        input.experience = "discovery"
    if input.lang not in ("fr", "en", "es"):
        input.lang = "fr"
    booking = Booking(**input.model_dump())
    if input.voucher_code:
        v = await redeem_voucher(db, input.voucher_code, booking.id)
        booking.voucher_code = v["code"]
        booking.discount = float(v["value"])
    booking.amount = price_of(booking.model_dump())
    doc = booking.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.bookings.insert_one(doc)
    await notify_owner(booking)
    await notify_client(booking)
    return booking


@api_router.post("/auth/login")
async def login(input: LoginInput, request: Request):
    return await auth_login(db, request, input.email, input.password)


@api_router.get("/auth/me")
async def me(admin: dict = Depends(require_admin)):
    return admin


@api_router.post("/auth/change-password")
async def auth_change_password(input: PasswordInput, admin: dict = Depends(require_admin)):
    await change_password(db, admin["email"], input.current_password, input.new_password)
    return {"ok": True}


@api_router.get("/bookings", response_model=List[Booking])
async def get_bookings(admin: dict = Depends(require_admin)):
    bookings = await db.bookings.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [_normalize(b) for b in bookings]


@api_router.get("/admin/settings")
async def admin_get_settings(admin: dict = Depends(require_admin)):
    return await get_settings()


@api_router.put("/admin/settings")
async def admin_put_settings(input: SettingsInput, admin: dict = Depends(require_admin)):
    data = input.model_dump()
    data["slot_times"] = _fit_slot_times(data.get("slot_times"), data["slots_per_day"])
    await db.settings.update_one({"key": "config"}, {"$set": data}, upsert=True)
    return await get_settings()


@api_router.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_admin)):
    bookings = await db.bookings.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    vouchers = await db.vouchers.find({}, {"_id": 0}).to_list(5000)
    stats = compute_stats(bookings, await get_settings(), vouchers)
    stats["vouchers"] = {"pending": sum(1 for v in vouchers if v["status"] == "pending"), "active": sum(1 for v in vouchers if v["status"] == "paid"),
                         "outstanding": sum(float(v["value"]) for v in vouchers if v["status"] == "paid")}
    stats["recent"] = [_normalize(b) for b in bookings[:10]]
    stats["total_bookings"] = len(bookings)
    return stats


@api_router.get("/admin/bookings", response_model=List[Booking])
async def admin_bookings(
    q: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=500, ge=1, le=5000),
    admin: dict = Depends(require_admin),
):
    f = _booking_filter(q, status, date_from, date_to)
    bookings = await db.bookings.find(f, {"_id": 0}).sort("date", -1).to_list(limit)
    return [_normalize(b) for b in bookings]


@api_router.get("/admin/bookings/export.csv")
async def admin_bookings_csv(
    q: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    admin: dict = Depends(require_admin),
):
    f = _booking_filter(q, status, date_from, date_to)
    bookings = await db.bookings.find(f, {"_id": 0}).sort("date", -1).to_list(5000)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["id", "date_session", "creneau", "statut", "client", "email", "telephone", "experience", "participants",
                "montant_eur", "bon_cadeau", "remise_eur", "partenaire", "nom_partenaire", "commission_eur", "hotel", "langue", "notes", "cree_le"])
    for b in bookings:
        b = _normalize(b)
        eligible = b.get("partner") and b.get("status") in ("confirmed", "completed")
        w.writerow([
            b["id"], b.get("date"), b.get("slot") or "", b.get("status"), b.get("name"), b.get("email"), b.get("phone"),
            b.get("experience"), b.get("participants"), f"{b['amount']:.2f}".replace(".", ","),
            b.get("voucher_code") or "", f"{float(b.get('discount') or 0):.2f}".replace(".", ","),
            "oui" if b.get("partner") else "non", b.get("partner_name") or "",
            f"{b['amount'] * 0.2:.2f}".replace(".", ",") if eligible else "0,00",
            b.get("hotel") or "", b.get("lang"), (b.get("notes") or "").replace("\n", " "), b["created_at"].isoformat(),
        ])
    filename = f"canary-foil-club-reservations-{datetime.now(timezone.utc).date().isoformat()}.csv"
    return StreamingResponse(
        iter(["\ufeff" + buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api_router.get("/admin/planning")
async def admin_planning(day: Optional[str] = None, admin: dict = Depends(require_admin)):
    d = _parse_day(day)
    bookings = await db.bookings.find({"date": {"$regex": f"^{d.isoformat()}"}}, {"_id": 0}).to_list(500)
    return compute_planning([_normalize(b) for b in bookings], d, await get_settings())


@api_router.get("/admin/planning/week")
async def admin_planning_week(start: Optional[str] = None, admin: dict = Depends(require_admin)):
    s = _parse_day(start)
    s = s - timedelta(days=s.weekday())
    end = s + timedelta(days=6)
    bookings = await db.bookings.find({"date": {"$gte": s.isoformat(), "$lte": end.isoformat() + "~"}}, {"_id": 0}).to_list(2000)
    return {"start": s.isoformat(), "end": end.isoformat(), "days": compute_week([_normalize(b) for b in bookings], s, await get_settings())}


@api_router.get("/admin/weather")
async def admin_weather(day: Optional[str] = None, admin: dict = Depends(require_admin)):
    return await get_weather(_parse_day(day).isoformat())


@api_router.get("/admin/planning/meeting-point")
async def admin_meeting_point(day: Optional[str] = None, admin: dict = Depends(require_admin)):
    mp = await meeting_point(db, _parse_day(day).isoformat())
    mp["options"] = [{"spot": k, "address": v} for k, v in SPOT_ADDRESS.items()]
    mp["reminder_hour"] = REMINDER_HOUR
    return mp


@api_router.put("/admin/planning/meeting-point")
async def admin_put_meeting_point(input: MeetingPointInput, admin: dict = Depends(require_admin)):
    d = _parse_day(input.date).isoformat()
    if not input.spot:
        await db.day_plans.delete_one({"date": d})
    else:
        await db.day_plans.update_one(
            {"date": d},
            {"$set": {"date": d, "spot": input.spot.strip(), "address": (input.address or SPOT_ADDRESS.get(input.spot.strip(), "")).strip(),
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    return await meeting_point(db, d)


@api_router.post("/admin/bookings/{booking_id}/reminder", response_model=Booking)
async def admin_send_reminder(booking_id: str, admin: dict = Depends(require_admin)):
    raw = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not raw:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    if raw.get("status") not in ("confirmed", "completed"):
        raise HTTPException(status_code=400, detail="Le rappel ne s'envoie qu'aux réservations confirmées")
    sent = await send_reminder(db, Booking, _normalize(raw), await get_settings(), force=True)
    if not sent:
        raise HTTPException(status_code=502, detail="Envoi du rappel impossible (email injoignable)")
    res = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    return _normalize(res)


@api_router.post("/admin/reminders/run")
async def admin_run_reminders(admin: dict = Depends(require_admin)):
    return await run_reminders(db, Booking, get_settings, _normalize)


# ---------- Reviews ----------

def _norm_review(r: dict) -> dict:
    for k in ("created_at", "replied_at"):
        if isinstance(r.get(k), datetime):
            r[k] = r[k].isoformat()
    return r


def _first_name(name: str) -> str:
    return (name or "").strip().split(" ")[0][:40] or "Client"


@api_router.get("/reviews", response_model=List[Review])
async def public_reviews(limit: int = Query(default=12, ge=1, le=50)):
    docs = await db.reviews.find({"approved": True}, {"_id": 0}).sort([("featured", -1), ("created_at", -1)]).to_list(limit)
    return [_norm_review(d) for d in docs]


@api_router.get("/reviews/{token}")
async def review_context(token: str):
    b = await db.bookings.find_one({"review_token": token}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Lien invalide ou expiré")
    existing = await db.reviews.find_one({"booking_id": b["id"]}, {"_id": 0})
    return {"name": _first_name(b["name"]), "experience": b["experience"], "date": b["date"], "lang": b.get("lang", "fr"),
            "already_reviewed": bool(existing), "review": _norm_review(existing) if existing else None}


@api_router.post("/reviews/{token}", response_model=Review)
async def submit_review(token: str, input: ReviewInput):
    b = await db.bookings.find_one({"review_token": token}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Lien invalide ou expiré")
    if await db.reviews.find_one({"booking_id": b["id"]}):
        raise HTTPException(status_code=409, detail="Un avis a déjà été déposé pour cette session")
    review = Review(
        id=str(uuid.uuid4()), booking_id=b["id"], name=(input.display_name or "").strip()[:60] or _first_name(b["name"]),
        rating=input.rating, comment=input.comment.strip(), lang=b.get("lang", "fr"), experience=b["experience"], date=str(b["date"])[:10],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    await db.reviews.insert_one(review.model_dump())
    await db.bookings.update_one({"id": b["id"]}, {"$set": {"review_id": review.id}})
    return review


@api_router.get("/admin/reviews", response_model=List[Review])
async def admin_reviews(admin: dict = Depends(require_admin)):
    return [_norm_review(d) for d in await db.reviews.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)]


@api_router.patch("/admin/reviews/{review_id}", response_model=Review)
async def admin_update_review(review_id: str, input: ReviewUpdate, admin: dict = Depends(require_admin)):
    update = {k: v for k, v in input.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="Aucune modification")
    if "reply" in update:
        update["reply"] = update["reply"].strip() or None
        update["replied_at"] = datetime.now(timezone.utc).isoformat() if update["reply"] else None
    res = await db.reviews.find_one_and_update({"id": review_id}, {"$set": update}, projection={"_id": 0}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    return _norm_review(res)


@api_router.delete("/admin/reviews/{review_id}")
async def admin_delete_review(review_id: str, admin: dict = Depends(require_admin)):
    res = await db.reviews.delete_one({"id": review_id})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    await db.bookings.update_one({"review_id": review_id}, {"$unset": {"review_id": ""}})
    return {"ok": True}


@api_router.post("/admin/bookings/{booking_id}/review-request", response_model=Booking)
async def admin_send_review_request(booking_id: str, admin: dict = Depends(require_admin)):
    raw = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not raw:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    if raw.get("status") not in ("confirmed", "completed"):
        raise HTTPException(status_code=400, detail="La demande d'avis ne s'envoie qu'aux sessions confirmées ou réalisées")
    sent = await send_review_request(db, Booking, _normalize(raw), force=True)
    if not sent:
        raise HTTPException(status_code=502, detail="Envoi impossible (email injoignable)")
    return _normalize(await db.bookings.find_one({"id": booking_id}, {"_id": 0}))


@api_router.post("/admin/reviews/run")
async def admin_run_review_requests(admin: dict = Depends(require_admin)):
    return await run_review_requests(db, Booking, _normalize)


# ---------- Gift vouchers ----------

VOUCHER_STATUSES = {"pending", "paid", "redeemed", "cancelled"}


@api_router.post("/vouchers", response_model=Voucher)
async def create_voucher(input: VoucherCreate):
    if input.experience not in VOUCHER_EXPERIENCES:
        input.experience = "discovery"
    if input.lang not in ("fr", "en", "es"):
        input.lang = "fr"
    participants = 2 if input.experience == "duo" else input.participants
    code = gen_code()
    while await db.vouchers.find_one({"code": code}):
        code = gen_code()
    v = Voucher(**{**input.model_dump(), "participants": participants}, id=str(uuid.uuid4()), code=code,
                value=voucher_value(input.experience, participants), created_at=datetime.now(timezone.utc).isoformat(),
                download_token=secrets.token_urlsafe(16))
    await db.vouchers.insert_one(v.model_dump())
    await notify_owner_voucher(v.model_dump())
    return v


@api_router.get("/vouchers/check/{code}")
async def check_voucher(code: str):
    v = await find_voucher(db, code)
    if not v:
        return {"valid": False, "reason": "not_found"}
    ok, reason = voucher_state(v)
    return {"valid": ok, "reason": reason, "value": v["value"] if ok else None, "experience": v["experience"] if ok else None,
            "participants": v["participants"] if ok else None, "recipient_name": v["recipient_name"] if ok else None}


def _voucher_pdf_url(v: dict) -> str:
    return f"{os.environ['SITE_URL'].rstrip('/')}/api/vouchers/{v['code']}/pdf?k={v.get('download_token', '')}"


def _pdf_response(v: dict) -> Response:
    pdf = build_voucher_pdf(v, os.environ["SITE_URL"])
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="bon-cadeau-{v["code"]}.pdf"'})


@api_router.get("/vouchers/{code}/pdf")
async def voucher_pdf(code: str, k: str = Query(min_length=8)):
    v = await find_voucher(db, code)
    if not v or not v.get("download_token") or not secrets.compare_digest(v["download_token"], k):
        raise HTTPException(status_code=404, detail="Bon cadeau introuvable")
    if v["status"] not in ("paid", "redeemed"):
        raise HTTPException(status_code=403, detail="Bon cadeau non activé")
    return _pdf_response(v)


@api_router.get("/admin/vouchers/{voucher_id}/pdf")
async def admin_voucher_pdf(voucher_id: str, admin: dict = Depends(require_admin)):
    v = await db.vouchers.find_one({"id": voucher_id}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Bon cadeau introuvable")
    if not v.get("expires_at"):
        v = {**v, "expires_at": None}
    return _pdf_response(v)


@api_router.get("/admin/vouchers", response_model=List[Voucher])
async def admin_vouchers(admin: dict = Depends(require_admin)):
    return await db.vouchers.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)


@api_router.patch("/admin/vouchers/{voucher_id}", response_model=Voucher)
async def admin_update_voucher(voucher_id: str, input: VoucherUpdate, admin: dict = Depends(require_admin)):
    if input.status not in VOUCHER_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    v = await db.vouchers.find_one({"id": voucher_id}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Bon cadeau introuvable")
    update = {"status": input.status}
    if input.status == "paid" and v["status"] != "paid":
        update.update(mark_paid_fields() if not v.get("paid_at") else {})
        if v["status"] == "redeemed":
            update.update({"redeemed_at": None, "redeemed_booking_id": None})
    await db.vouchers.update_one({"id": voucher_id}, {"$set": update})
    v = await db.vouchers.find_one({"id": voucher_id}, {"_id": 0})
    if input.status == "paid" and not v.get("email_sent"):
        sent = await notify_voucher_buyer(v, _voucher_pdf_url(v))
        await db.vouchers.update_one({"id": voucher_id}, {"$set": {"email_sent": sent}})
        v["email_sent"] = sent
    return v


@api_router.post("/admin/vouchers/{voucher_id}/resend", response_model=Voucher)
async def admin_resend_voucher(voucher_id: str, admin: dict = Depends(require_admin)):
    v = await db.vouchers.find_one({"id": voucher_id}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Bon cadeau introuvable")
    if v["status"] not in ("paid", "redeemed"):
        raise HTTPException(status_code=400, detail="Activez d'abord le bon (paiement reçu)")
    sent = await notify_voucher_buyer(v, _voucher_pdf_url(v))
    if not sent:
        raise HTTPException(status_code=502, detail="Envoi impossible (email injoignable)")
    await db.vouchers.update_one({"id": voucher_id}, {"$set": {"email_sent": True}})
    return {**v, "email_sent": True}


# ---------- Weekly report ----------

@api_router.get("/admin/reports/weekly")
async def admin_weekly_preview(admin: dict = Depends(require_admin)):
    report = await build_weekly_report(db, await get_settings())
    last = await db.weekly_reports.find_one({"week_start": report["week_start"]}, {"_id": 0})
    report["last_sent"] = last
    return report


@api_router.post("/admin/reports/weekly/send")
async def admin_weekly_send(to: Optional[EmailStr] = None, admin: dict = Depends(require_admin)):
    res = await run_weekly_report(db, get_settings, force=True, to=to)
    if not res["sent"]:
        raise HTTPException(status_code=502, detail="Envoi du bilan impossible (email propriétaire injoignable)")
    return res


@api_router.patch("/admin/bookings/{booking_id}", response_model=Booking)
async def update_booking(booking_id: str, input: BookingUpdate, admin: dict = Depends(require_admin)):
    update = {k: v for k, v in input.model_dump().items() if v is not None}
    if "status" in update and update["status"] not in STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    if not update:
        raise HTTPException(status_code=400, detail="Aucune modification")
    if update.get("slot") == 0:
        update["slot"] = None
    before = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not before:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.bookings.find_one_and_update({"id": booking_id}, {"$set": update}, projection={"_id": 0}, return_document=True)
    booking = Booking(**_normalize(res))
    if update.get("status") == "confirmed" and before.get("status") != "confirmed":
        sent = await notify_confirmed(booking, slot_label(await get_settings(), booking.slot))
        await db.bookings.update_one({"id": booking_id}, {"$set": {"confirmation_email_sent": sent}})
        booking.confirmation_email_sent = sent
    return booking


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup():
    await seed_admin(db)
    await db.reviews.create_index("booking_id", unique=True)
    await db.bookings.create_index("review_token")
    await db.vouchers.create_index("code", unique=True)

    async def reviews_job():
        if datetime.now(CANARY_TZ).hour >= REVIEW_HOUR:
            await run_review_requests(db, Booking, _normalize)

    async def report_job():
        await run_weekly_report(db, get_settings)

    app.state.jobs = [
        asyncio.create_task(reminder_loop(db, Booking, get_settings, _normalize)),
        asyncio.create_task(periodic("reviews", reviews_job)),
        asyncio.create_task(periodic("weekly-report", report_job)),
    ]


@app.on_event("shutdown")
async def shutdown_db_client():
    for task in getattr(app.state, "jobs", []):
        task.cancel()
    client.close()
