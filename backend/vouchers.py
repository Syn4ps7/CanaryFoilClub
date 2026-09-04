import secrets
import string
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from stats import PRICES

VOUCHER_EXPERIENCES = {"discovery", "duo"}
VALIDITY_DAYS = 365
_ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"


def gen_code() -> str:
    chunk = lambda: "".join(secrets.choice(_ALPHABET) for _ in range(4))
    return f"CFC-{chunk()}-{chunk()}"


def voucher_value(experience: str, participants: int) -> float:
    if experience == "duo":
        return float(PRICES["duo"])
    return float(PRICES["discovery"] * participants)


def voucher_state(v: dict, now: datetime | None = None) -> tuple[bool, str]:
    now = now or datetime.now(timezone.utc)
    st = v.get("status")
    if st == "pending":
        return False, "unpaid"
    if st == "cancelled":
        return False, "cancelled"
    if st == "redeemed":
        return False, "redeemed"
    exp = v.get("expires_at")
    if exp and datetime.fromisoformat(exp) < now:
        return False, "expired"
    return st == "paid", "ok" if st == "paid" else st


async def find_voucher(db, code: str) -> dict | None:
    code = (code or "").strip().upper().replace(" ", "")
    if not code:
        return None
    return await db.vouchers.find_one({"code": code}, {"_id": 0})


async def redeem_voucher(db, code: str, booking_id: str) -> dict:
    v = await find_voucher(db, code)
    if not v:
        raise HTTPException(status_code=400, detail="Code cadeau introuvable")
    ok, reason = voucher_state(v)
    if not ok:
        raise HTTPException(status_code=400, detail={"unpaid": "Ce bon cadeau n'est pas encore activé", "cancelled": "Ce bon cadeau a été annulé",
                                                      "redeemed": "Ce bon cadeau a déjà été utilisé", "expired": "Ce bon cadeau a expiré"}.get(reason, "Bon cadeau invalide"))
    await db.vouchers.update_one(
        {"id": v["id"]},
        {"$set": {"status": "redeemed", "redeemed_at": datetime.now(timezone.utc).isoformat(), "redeemed_booking_id": booking_id}},
    )
    return v


def mark_paid_fields() -> dict:
    now = datetime.now(timezone.utc)
    return {"status": "paid", "paid_at": now.isoformat(), "expires_at": (now + timedelta(days=VALIDITY_DAYS)).isoformat()}
