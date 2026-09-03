import hmac
import hashlib
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session

from ..auth import verify_api_key
from ..database import get_db, SessionLocal
from ..models import WebhookEvent, Payment, Order, Decision
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhooks/razorpay")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    payload = await request.body()

    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=400, detail="Webhook secret not configured.")
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header.")
    if not verify_webhook_signature(payload, x_razorpay_signature, secret):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        payload_json = json.loads(payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed JSON body.")

    event_id = x_razorpay_event_id or payload_json.get("id")
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event ID.")

    existing = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if existing:
        return {"status": "ignored", "message": "Duplicate event ignored", "event_id": event_id}

    event_type = payload_json.get("event", "unknown")
    event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        entity_id=_extract_entity_id(payload_json),
        status="accepted",
        payload=str(payload_json),
    )
    db.add(event)
    db.commit()
    background_tasks.add_task(process_webhook_event, payload_json, event_id)
    return {"status": "accepted", "event_id": event_id}


def _extract_entity_id(payload: dict) -> str | None:
    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order = payload.get("payload", {}).get("order", {}).get("entity", {})
    return payment.get("id") or order.get("id")


def process_webhook_event(payload: dict, event_id: str):
    db = SessionLocal()
    event = None
    try:
        event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
        if not event:
            return
        event.status = "processing"
        db.commit()

        event_type = payload.get("event", "")
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        payment_id = payment_entity.get("id")
        order_id = payment_entity.get("order_id") or order_entity.get("id")

        if payment_id:
            _upsert_payment(db, payment_id, order_id, payment_entity, payload)
        if event_type == "order.paid" and order_entity:
            _handle_order_paid(db, order_entity)
        if event_type == "payment.captured":
            _handle_payment_captured(db, payment_id, order_id)
        elif event_type == "payment.authorized":
            _handle_payment_authorized(db, payment_id)
        elif event_type == "payment.failed":
            _handle_payment_failed(db, payment_id)
        elif event_type == "refund.processed":
            _handle_refund_processed(db, payment_id)

        event.status = "processed"
        event.processed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        if event:
            event.status = "failed"
            event.error_message = str(e)
            db.commit()
    finally:
        db.close()


def _upsert_payment(db, payment_id: str, order_id: str | None, entity: dict, raw_payload: dict):
    payment = db.query(Payment).filter(Payment.razorpay_payment_id == payment_id).first()
    data = {
        "razorpay_order_id": order_id,
        "amount": entity.get("amount", 0),
        "currency": entity.get("currency", "INR"),
        "status": entity.get("status", "unknown"),
        "method": entity.get("method"),
        "bank": entity.get("bank"),
        "wallet": entity.get("wallet"),
        "vpa": entity.get("vpa"),
        "email": entity.get("email"),
        "contact": entity.get("contact"),
        "error_code": entity.get("error_code"),
        "error_description": entity.get("error_description"),
        "error_source": entity.get("error_source"),
        "error_step": entity.get("error_step"),
        "error_reason": entity.get("error_reason"),
        "raw_payload": str(raw_payload),
    }
    if payment:
        for k, v in data.items():
            setattr(payment, k, v)
    else:
        db.add(Payment(razorpay_payment_id=payment_id, **data))
    db.commit()


def _handle_order_paid(db, order_entity: dict):
    """Update or create order when order.paid event arrives."""
    order_id = order_entity.get("id")
    order = db.query(Order).filter(Order.razorpay_order_id == order_id).first()
    if order:
        order.status = "paid"
    else:
        db.add(Order(
            razorpay_order_id=order_id,
            amount=order_entity.get("amount", 0),
            currency=order_entity.get("currency", "INR"),
            status="paid",
            receipt=order_entity.get("receipt"),
        ))
    db.commit()


def _handle_payment_captured(db, payment_id: str | None, order_id: str | None):
    if order_id:
        order = db.query(Order).filter(Order.razorpay_order_id == order_id).first()
        if order:
            order.status = "paid"
            db.commit()
    if payment_id:
        decision = db.query(Decision).filter(Decision.transaction_id == payment_id).first()
        if decision:
            decision.outcome = "legitimate"
            db.commit()


def _handle_payment_authorized(db, payment_id: str | None):
    if payment_id:
        decision = db.query(Decision).filter(Decision.transaction_id == payment_id).first()
        if decision:
            decision.outcome = "authorized"
            db.commit()


def _handle_payment_failed(db, payment_id: str | None):
    if payment_id:
        decision = db.query(Decision).filter(Decision.transaction_id == payment_id).first()
        if decision:
            decision.outcome = "fraudulent"
            db.commit()


def _handle_refund_processed(db, payment_id: str | None):
    if payment_id:
        decision = db.query(Decision).filter(Decision.transaction_id == payment_id).first()
        if decision:
            decision.outcome = "refunded"
            db.commit()


def verify_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature or not payload_body:
        return False
    try:
        expected = hmac.new(secret.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


@router.get("/webhooks", tags=["Webhooks"])
def list_webhooks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    """List webhook events. Requires X-API-Key."""
    events = db.query(WebhookEvent).order_by(WebhookEvent.created_at.desc()).offset(skip).limit(limit).all()
    return {"events": events, "total": db.query(WebhookEvent).count(), "skip": skip, "limit": limit}


@router.get("/webhooks/{event_id}", tags=["Webhooks"])
def get_webhook_event(
    event_id: str,
    db: Session = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    """Get a webhook event. Requires X-API-Key."""
    event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    return event
