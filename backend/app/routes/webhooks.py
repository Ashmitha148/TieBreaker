import hmac
import hashlib
import logging
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models import WebhookEvent, Payment, Order, Decision
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Receive Razorpay webhooks asynchronously.
    Verifies HMAC signature, stores raw payload, and processes asynchronously.
    """
    payload = await request.body()

    # Verify webhook signature
    secret = settings.RAZORPAY_KEY_SECRET
    if secret and x_razorpay_signature:
        if not verify_webhook_signature(payload, x_razorpay_signature, secret):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload_json = await request.json()
    except Exception:
        payload_json = {"raw_body": payload.decode("utf-8", errors="replace")}

    # Create initial webhook event record synchronously
    event = WebhookEvent(
        event_id=payload_json.get("id", str(uuid4())),
        event_type=payload_json.get("event", "unknown"),
        entity_id=payload_json.get("payload", {}).get("payment", {}).get("entity", {}).get("id"),
        status="received",
        payload=str(payload_json),
    )
    db.add(event)
    db.commit()

    # Process webhook asynchronously
    background_tasks.add_task(process_webhook_event, payload_json)

    return {"status": "received", "event_id": event.event_id}


def process_webhook_event(payload: dict):
    """
    Process a Razorpay webhook event asynchronously.
    Creates its own DB session - do NOT pass the request-scoped session here.
    """
    db = SessionLocal()
    try:
        # Create webhook event record
        event = WebhookEvent(
            event_id=payload.get("id", str(uuid4())),
            event_type=payload.get("event", "unknown"),
            entity_id=payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id"),
            status="processing",
            payload=str(payload),
        )
        db.add(event)
        db.commit()

        event_type = payload.get("event", "")
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

        # Update payment status
        payment_id = payment_entity.get("id")
        if payment_id:
            payment = db.query(Payment).filter(
                Payment.razorpay_payment_id == payment_id
            ).first()

            if payment:
                payment.status = payment_entity.get("status", payment.status)
                payment.method = payment_entity.get("method", payment.method)
                payment.bank = payment_entity.get("bank", payment.bank)
                payment.wallet = payment_entity.get("wallet", payment.wallet)
                payment.vpa = payment_entity.get("vpa", payment.vpa)
                payment.email = payment_entity.get("email", payment.email)
                payment.contact = payment_entity.get("contact", payment.contact)
                payment.error_code = payment_entity.get("error_code", payment.error_code)
                payment.error_description = payment_entity.get("error_description", payment.error_description)
                payment.error_source = payment_entity.get("error_source", payment.error_source)
                payment.error_step = payment_entity.get("error_step", payment.error_step)
                payment.error_reason = payment_entity.get("error_reason", payment.error_reason)
                payment.raw_payload = str(payload)
                db.commit()

        # Handle specific event types
        if event_type == "payment.captured":
            order_id = payment_entity.get("order_id")
            if order_id:
                order = db.query(Order).filter(
                    Order.razorpay_order_id == order_id
                ).first()
                if order:
                    order.status = "paid"
                    db.commit()

            # Update decision outcome
            decision = db.query(Decision).filter(
                Decision.transaction_id == payment_id
            ).first()
            if decision:
                decision.outcome = "legitimate"
                db.commit()

        elif event_type == "payment.failed":
            # Update decision outcome for failed payments
            decision = db.query(Decision).filter(
                Decision.transaction_id == payment_id
            ).first()
            if decision:
                decision.outcome = "fraudulent"
                db.commit()

        elif event_type == "refund.processed":
            # Update decision outcome for refunds
            decision = db.query(Decision).filter(
                Decision.transaction_id == payment_id
            ).first()
            if decision:
                decision.outcome = "refunded"
                db.commit()

        # Mark event as processed
        event.status = "processed"
        event.processed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Webhook event {event.event_id} processed successfully")

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # Update event status to failed
        event.status = "failed"
        event.error_message = str(e)
        db.commit()
    finally:
        db.close()


def verify_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """
    Verify Razorpay webhook signature using HMAC-SHA256.
    """
    try:
        expected_signature = hmac.new(
            secret.encode(),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


@router.get("/webhooks", tags=["Webhooks"])
def list_webhooks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all received webhook events."""
    events = db.query(WebhookEvent).order_by(
        WebhookEvent.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "events": events,
        "total": db.query(WebhookEvent).count(),
        "skip": skip,
        "limit": limit,
    }


@router.get("/webhooks/{event_id}", tags=["Webhooks"])
def get_webhook_event(
    event_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific webhook event by ID."""
    event = db.query(WebhookEvent).filter(
        WebhookEvent.event_id == event_id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")

    return event