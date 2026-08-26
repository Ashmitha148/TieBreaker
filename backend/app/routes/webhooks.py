import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import WebhookEvent
from ..schemas import WebhookResponse
from ..services.razorpay_service import verify_webhook_signature
from ..services.webhook_processor import process_webhook_event_task

logger = logging.getLogger("tiebreaker.webhook_route")
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/razorpay", response_model=WebhookResponse, status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Razorpay Webhook Handler:
    1. Reads raw request body.
    2. Validates X-Razorpay-Signature with HMAC-SHA256 against RAZORPAY_WEBHOOK_SECRET.
    3. Enforces idempotency via X-Razorpay-Event-Id / payload id.
    4. Persists the event log immediately.
    5. Dispatches asynchronous processing to background tasks.
    6. Quickly responds with HTTP 200.
    """
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty webhook request body",
        )

    signature = request.headers.get("X-Razorpay-Signature") or request.headers.get("x-razorpay-signature")
    if not signature:
        logger.warning("Webhook received without X-Razorpay-Signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header",
        )

    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not webhook_secret:
        logger.error("RAZORPAY_WEBHOOK_SECRET is not configured on the server")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured on server",
        )

    is_valid = verify_webhook_signature(raw_body, signature, webhook_secret)
    if not is_valid:
        logger.warning("Invalid webhook signature received")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    try:
        payload_data = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.warning(f"Malformed JSON in webhook body: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON in webhook body",
        )

    event_id = (
        request.headers.get("X-Razorpay-Event-Id")
        or request.headers.get("x-razorpay-event-id")
        or payload_data.get("event_id")
        or payload_data.get("id")
    )
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event ID for webhook",
        )

    event_type = payload_data.get("event", "unknown")
    entity_id = (
        payload_data.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
        or payload_data.get("payload", {}).get("order", {}).get("entity", {}).get("id")
    )

    existing_event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if existing_event:
        logger.info(f"Duplicate webhook event ignored: {event_id} ({event_type})")
        return WebhookResponse(
            status="ignored",
            message="Duplicate event ignored",
            event_id=event_id,
        )

    webhook_event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        entity_id=entity_id,
        status="received",
        payload=raw_body.decode("utf-8"),
    )
    db.add(webhook_event)
    db.commit()

    background_tasks.add_task(
        process_webhook_event_task,
        event_id=event_id,
        event_type=event_type,
        payload_data=payload_data,
    )

    return WebhookResponse(
        status="accepted",
        message="Webhook received and queued for processing",
        event_id=event_id,
    )