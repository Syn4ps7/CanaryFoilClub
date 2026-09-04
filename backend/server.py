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
from datetime import datetime, timezone, date, timedelta
from emailer import notify_owner, notify_client, notify_confirmed
from auth import login as auth_login, seed_admin, get_current_admin_factory, change_password
from stats import compute_stats, compute_planning, compute_week, price_of, DEFAULT_SETTINGS, MAX_BOARDS, MAX_SLOTS
from weather import get_weather

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
    lang: str = "fr"


class Booking(BookingCreate):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    amount: float = 0
    slot: Optional[int] = None
    confirmation_email_sent: Optional[bool] = None
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
    return {**DEFAULT_SETTINGS, **(doc or {})}


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
    await db.settings.update_one({"key": "config"}, {"$set": input.model_dump()}, upsert=True)
    return await get_settings()


@api_router.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_admin)):
    bookings = await db.bookings.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    stats = compute_stats(bookings, await get_settings())
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
                "montant_eur", "partenaire", "nom_partenaire", "commission_eur", "hotel", "langue", "notes", "cree_le"])
    for b in bookings:
        b = _normalize(b)
        eligible = b.get("partner") and b.get("status") in ("confirmed", "completed")
        w.writerow([
            b["id"], b.get("date"), b.get("slot") or "", b.get("status"), b.get("name"), b.get("email"), b.get("phone"),
            b.get("experience"), b.get("participants"), f"{b['amount']:.2f}".replace(".", ","),
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
        sent = await notify_confirmed(booking)
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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
