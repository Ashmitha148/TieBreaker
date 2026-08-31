from fastapi import APIRouter, Depends, HTTPException, Header, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import hashlib
import hmac
import json
import logging

from ..database import get_db, SessionLocal
from ..models import WebhookEvent, Payment, Order, Decision
from ..config import settings

router = APIRouter()
logger = logging.getLogger("tiebreaker.webhooks")


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _process_webhook_event(event_type: str, payload: dict):
    """
    Background task: process webhook event with its OWN SessionLocal.
    NEVER uses a request-scoped DB session.
    """
    db = SessionLocal()
    try:
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        if not entity:
            entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        payment_id = entity.get("id", "")
        order_id = entity.get("order_id", "")
        status = entity.get("status", "")
        amount = entity.get("amount", 0)
        method = entity.get("method", "")

        payment = db.query(Payment).filter(Payment.razorpay_payment_id == payment_id).first()
        if payment:
            payment.status = status
            payment.method = method
            payment.raw_payload = json.dumps(payload)
        else:
            order = db.query(Order).filter(Order.razorpay_order_id == order_id).first()
            new_payment = Payment(
                razorpay_payment_id=payment_id,
                razorpay_order_id=order_id,
                order_id=order.id if order else None,
                amount=amount,
                status=status,
                method=method,
                raw_payload=json.dumps(payload),
            )
            db.add(new_payment)

        # Update Decision outcome for payment.captured / payment.failed / refund.processed
        if event_type in ("payment.captured", "payment.failed", "refund.processed"):
            decision = db.query(Decision).filter(Decision.transaction_id == order_id).first()
            if decision:
                if event_type == "payment.captured":
                    decision.outcome = "captured"
                elif event_type == "payment.failed":
                    decision.outcome = "failed"
                elif event_type == "refund.processed":
                    decision.outcome = "refunded"

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Webhook background processing failed: {e}")
        raise
    finally:
        db.close()


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_razorpay_event_id: Optional[str] = Header(None),
    x_razorpay_signature: Optional[str] = Header(None),
):
    body = await request.body()
    payload = await request.json()
    event_type = payload.get("event", "unknown")

    secret = settings.RAZORPAY_WEBHOOK_SECRET or settings.RAZORPAY_KEY_SECRET or ""
    # Fail CLOSED: verify before touching the DB at all
    if not secret:
        raise HTTPException(status_code=401, detail="Webhook secret not configured")
    if not x_razorpay_signature:
        raise HTTPException(status_code=401, detail="Missing signature")
    if not verify_webhook_signature(body, x_razorpay_signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    if x_razorpay_event_id:
        existing = db.query(WebhookEvent).filter(WebhookEvent.event_id == x_razorpay_event_id).first()
        if existing:
            return {"status": "already_processed", "event_id": x_razorpay_event_id}

    event = WebhookEvent(
        event_id=x_razorpay_event_id or f"evt_{hashlib.md5(body).hexdigest()[:12]}",
        event_type=event_type,
        entity_id=payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id", ""),
        status="received",
        payload=json.dumps(payload),
    )
    db.add(event)
    db.commit()

    # Background task uses its own SessionLocal — never the request-scoped db
    background_tasks.add_task(_process_webhook_event, event_type, payload)
    return {"status": "received", "event_id": event.event_id}


@router.get("/webhooks")
def list_webhooks(db: Session = Depends(get_db)):
    events = db.query(WebhookEvent).order_by(WebhookEvent.created_at.desc()).limit(50).all()
    return {
        "events": [
            {
                "id": e.id,
                "event_id": e.event_id,
                "event_type": e.event_type,
                "entity_id": e.entity_id,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    }