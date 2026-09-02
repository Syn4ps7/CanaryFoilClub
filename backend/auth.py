import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request

JWT_ALGORITHM = "HS256"
ACCESS_HOURS = 12
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(email: str) -> str:
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_HOURS),
        "type": "access",
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


async def seed_admin(db):
    email = os.environ["ADMIN_EMAIL"].lower()
    password = os.environ["ADMIN_PASSWORD"]
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    existing = await db.users.find_one({"email": email})
    if existing is None:
        await db.users.insert_one({
            "email": email,
            "password_hash": hash_password(password),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif not verify_password(password, existing["password_hash"]):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(password)}})


async def check_lockout(db, identifier: str):
    rec = await db.login_attempts.find_one({"identifier": identifier})
    if not rec:
        return
    locked_until = rec.get("locked_until")
    if locked_until and datetime.fromisoformat(locked_until) > datetime.now(timezone.utc):
        raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez dans 15 minutes.")


async def register_failure(db, identifier: str):
    rec = await db.login_attempts.find_one({"identifier": identifier})
    count = (rec.get("count", 0) if rec else 0) + 1
    update = {"count": count, "last_at": datetime.now(timezone.utc).isoformat()}
    if count >= MAX_ATTEMPTS:
        update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)).isoformat()
        update["count"] = 0
    await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)


async def clear_failures(db, identifier: str):
    await db.login_attempts.delete_one({"identifier": identifier})


async def login(db, request: Request, email: str, password: str) -> dict:
    email = email.strip().lower()
    identifier = email
    await check_lockout(db, identifier)
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(password, user["password_hash"]):
        await register_failure(db, identifier)
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    await clear_failures(db, identifier)
    return {"token": create_access_token(email), "email": email, "role": user.get("role", "admin")}


def get_current_admin_factory(db):
    async def get_current_admin(request: Request) -> dict:
        token = request.cookies.get("access_token")
        if not token:
            header = request.headers.get("Authorization", "")
            if header.startswith("Bearer "):
                token = header[7:]
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Session expirée")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token invalide")
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token invalide")
        user = await db.users.find_one({"email": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user or user.get("role") != "admin":
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")
        return user

    return get_current_admin
