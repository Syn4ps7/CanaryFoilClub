from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emailer import notify_owner, notify_client
from auth import login as auth_login, seed_admin, get_current_admin_factory
from stats import compute_stats, price_of

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    partner: Optional[bool] = None
    partner_name: Optional[str] = Field(default=None, max_length=120)


def _normalize(b: dict) -> dict:
    if isinstance(b.get('created_at'), str):
        b['created_at'] = datetime.fromisoformat(b['created_at'])
    b.setdefault('partner', False)
    b['amount'] = price_of(b)
    return b


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


@api_router.get("/bookings", response_model=List[Booking])
async def get_bookings(admin: dict = Depends(require_admin)):
    bookings = await db.bookings.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [_normalize(b) for b in bookings]


@api_router.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_admin)):
    bookings = await db.bookings.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    stats = compute_stats(bookings)
    stats["recent"] = [_normalize(b) for b in bookings[:10]]
    stats["total_bookings"] = len(bookings)
    return stats


@api_router.patch("/admin/bookings/{booking_id}", response_model=Booking)
async def update_booking(booking_id: str, input: BookingUpdate, admin: dict = Depends(require_admin)):
    update = {k: v for k, v in input.model_dump().items() if v is not None}
    if "status" in update and update["status"] not in STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    if not update:
        raise HTTPException(status_code=400, detail="Aucune modification")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.bookings.find_one_and_update({"id": booking_id}, {"$set": update}, projection={"_id": 0}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    return _normalize(res)


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
