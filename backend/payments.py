import os
import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
LABELS = {"discovery": "Discovery Session", "duo": "Duo VIP Experience", "drone": "Option Drone 4K", "corporate": "Corporate Sunset", "testdrive": "Test Drive"}


class CheckoutRequest(BaseModel):
    kind: str
    ref_id: str
    origin_url: str


def build_router(db, fulfill):
    router = APIRouter(prefix="/api/payments")

    async def _mark_paid(session_id: str, s=None) -> dict | None:
        rec = await db.payment_transactions.find_one_and_update(
            {"session_id": session_id, "payment_status": {"$ne": "paid"}},
            {"$set": {"status": "completed", "payment_status": "paid", "updated_at": datetime.now(timezone.utc).isoformat(),
                      "stripe_payment_intent_id": getattr(s, "payment_intent", None) if s else None}},
            projection={"_id": 0},
        )
        if rec:
            await fulfill(rec["kind"], rec["ref_id"], session_id)
        return rec

    @router.post("/checkout")
    async def create_checkout(req: CheckoutRequest):
        if req.kind == "booking":
            doc = await db.bookings.find_one({"id": req.ref_id}, {"_id": 0})
            if not doc:
                raise HTTPException(404, "Réservation introuvable")
            from stats import price_of
            amount = price_of(doc)
            name = f"{LABELS.get(doc['experience'], doc['experience'])} · {doc['participants']} pers. · {doc['date']}"
            email = doc["email"]
            if doc.get("status") in ("confirmed", "completed"):
                raise HTTPException(400, "Réservation déjà confirmée")
        elif req.kind == "voucher":
            doc = await db.vouchers.find_one({"id": req.ref_id}, {"_id": 0})
            if not doc:
                raise HTTPException(404, "Bon cadeau introuvable")
            amount = float(doc["value"])
            name = f"Bon cadeau {LABELS.get(doc['experience'], doc['experience'])} pour {doc['recipient_name']}"
            email = doc["buyer_email"]
            if doc.get("status") != "pending":
                raise HTTPException(400, "Bon cadeau déjà réglé")
        else:
            raise HTTPException(400, "Type invalide")
        if amount <= 0:
            raise HTTPException(400, "Aucun paiement requis (montant nul)")
        kwargs = dict(
            mode="payment",
            line_items=[{"price_data": {"currency": "eur", "unit_amount": int(round(amount * 100)), "product_data": {"name": f"Canary Foil Club — {name}"}}, "quantity": 1}],
            customer_email=email,
            success_url=f"{req.origin_url}/paiement?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{req.origin_url}/paiement?cancelled=1&kind={req.kind}",
            metadata={"kind": req.kind, "ref_id": req.ref_id},
        )
        try:
            session = stripe.checkout.Session.create(**kwargs, automatic_tax={"enabled": True}, billing_address_collection="required")
        except stripe.error.StripeError:
            session = stripe.checkout.Session.create(**kwargs)
        await db.payment_transactions.insert_one({
            "session_id": session.id, "kind": req.kind, "ref_id": req.ref_id, "amount": float(amount), "currency": "eur",
            "status": "initiated", "payment_status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.get("/status/{session_id}")
    async def get_status(session_id: str):
        rec = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if not rec:
            raise HTTPException(404, "Transaction introuvable")
        if rec["payment_status"] != "paid":
            try:
                s = stripe.checkout.Session.retrieve(session_id)
                if s.payment_status == "paid" or s.status == "complete":
                    await _mark_paid(session_id, s)
                    rec = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
            except stripe.error.StripeError:
                pass
        return {"session_id": rec["session_id"], "status": rec["status"], "payment_status": rec["payment_status"], "kind": rec["kind"], "amount": rec["amount"]}

    return router, _mark_paid


def make_webhook(db, mark_paid):
    async def stripe_webhook(request: Request):
        payload = await request.body()
        try:
            event = stripe.Webhook.construct_event(payload, request.headers.get("stripe-signature", ""), WEBHOOK_SECRET)
        except (stripe.error.SignatureVerificationError, ValueError):
            raise HTTPException(400, "Invalid signature")
        obj, t = event["data"]["object"], event["type"]
        now = datetime.now(timezone.utc).isoformat()
        if t in ("checkout.session.completed", "checkout.session.async_payment_succeeded") and obj.get("payment_status", "paid") == "paid":
            await mark_paid(obj["id"])
        elif t == "checkout.session.async_payment_failed":
            await db.payment_transactions.update_one({"session_id": obj["id"]}, {"$set": {"status": "failed", "payment_status": "failed", "updated_at": now}})
        elif t == "checkout.session.expired":
            await db.payment_transactions.update_one({"session_id": obj["id"]}, {"$set": {"status": "expired", "payment_status": "expired", "updated_at": now}})
        elif t == "charge.refunded":
            await db.payment_transactions.update_one({"stripe_payment_intent_id": obj.get("payment_intent")}, {"$set": {"status": "refunded", "payment_status": "refunded", "updated_at": now}})
        return {"status": "ok"}
    return stripe_webhook
