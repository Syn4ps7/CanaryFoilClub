from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emailer import notify_owner

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

EXPERIENCES = {"discovery", "duo", "drone", "corporate", "testdrive"}


class BookingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=30)
    experience: str
    date: str = Field(min_length=4, max_length=40)
    participants: int = Field(ge=1, le=12)
    hotel: Optional[str] = None
    notes: Optional[str] = None
    lang: str = "fr"


class Booking(BookingCreate):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    doc = booking.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.bookings.insert_one(doc)
    from emailer import notify_client
    await notify_owner(booking)
    await notify_client(booking)
    return booking


@api_router.get("/bookings", response_model=List[Booking])
async def get_bookings():
    bookings = await db.bookings.find({}, {"_id": 0}).to_list(1000)
    for b in bookings:
        if isinstance(b.get('created_at'), str):
            b['created_at'] = datetime.fromisoformat(b['created_at'])
    return bookings


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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
