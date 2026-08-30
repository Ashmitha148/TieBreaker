from fastapi import APIRouter, Depends, HTTPException, Header, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import hashlib
import hmac
import json
import logging

from ..database import get_db
from ..models import WebhookEvent
from ..config import settings
from ..services.webhook_processor import process_webhook_event_task

router = APIRouter()
logger = logging.getLogger("tiebreaker.webhooks")


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_razorpay_event_id: Optional[str] = Header(None),
    x_razorpay_signature: Optional[str] = Header(None),
):
    body = await request.body()

    # FIXED: a raw request.json() call on an empty or malformed body used to
    # raise an uncaught json.decoder.JSONDecodeError -> 500, instead of the
    # 400 Razorpay delivery retries expect on a bad payload.
    if not body:
        raise HTTPException(status_code=400, detail="Empty webhook body")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed JSON in webhook body")

    event_type = payload.get("event", "unknown")

    # Verify authenticity before trusting anything else in the request,
    # including the event id used for the idempotency check below.
    secret = settings.RAZORPAY_WEBHOOK_SECRET or settings.RAZORPAY_KEY_SECRET or ""
    if secret and len(secret) > 5:
        if not x_razorpay_signature:
            raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")
        if not verify_webhook_signature(body, x_razorpay_signature, secret):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # FIXED: previously always synthesized an id (md5 of the body) when the
    # header was absent, so a delivery with no real id could never be
    # rejected or deduplicated correctly. Now falls back to a body-level id
    # and only then fails loudly.
    event_id = x_razorpay_event_id or payload.get("id")
    if not event_id:
        raise HTTPException(
            status_code=400,
            detail="Missing event ID: no X-Razorpay-Event-Id header and no id in payload",
        )

    existing = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if existing:
        return {"status": "ignored", "event_id": event_id, "message": "Duplicate event ignored"}

    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    if not entity:
        entity = payload.get("payload", {}).get("order", {}).get("entity", {})

    event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        entity_id=entity.get("id", ""),
        status="received",
        payload=json.dumps(payload),
    )
    db.add(event)
    db.commit()

    # FIXED: the background task now opens its own DB session
    # (process_webhook_event_task does this internally via SessionLocal()).
    # Passing the request-scoped `db` session here was a real bug: FastAPI
    # closes it via get_db()'s `finally` block during request teardown,
    # which happens before the background task actually runs, so writes
    # inside it were silently lost.
    background_tasks.add_task(process_webhook_event_task, event_id, event_type, payload)

    return {"status": "accepted", "event_id": event_id}


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