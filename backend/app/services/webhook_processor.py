import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Order, Payment, WebhookEvent

logger = logging.getLogger("tiebreaker.webhook_processor")


def process_webhook_event_task(event_id: str, event_type: str, payload_data: Dict[str, Any]):
    """
    Asynchronous background worker for processing verified Razorpay webhook events.
    Is resilient and event-order tolerant: updates/upserts payment and order records
    regardless of the event arrival order.
    """
    db: Session = SessionLocal()
    try:
        event_record = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()

        payload = payload_data.get("payload", {})
        payment_entity = payload.get("payment", {}).get("entity")
        order_entity = payload.get("order", {}).get("entity")

        # 1. Process payment payload if present (payment.authorized, payment.captured, payment.failed, etc.)
        if payment_entity:
            razorpay_payment_id = payment_entity.get("id")
            razorpay_order_id = payment_entity.get("order_id")
            amount = payment_entity.get("amount", 0)
            currency = payment_entity.get("currency", "INR")
            payment_status = payment_entity.get("status", "unknown")
            method = payment_entity.get("method")
            bank = payment_entity.get("bank")
            wallet = payment_entity.get("wallet")
            vpa = payment_entity.get("vpa")
            email = payment_entity.get("email")
            contact = payment_entity.get("contact")
            error_code = payment_entity.get("error_code")
            error_description = payment_entity.get("error_description")
            error_source = payment_entity.get("error_source")
            error_step = payment_entity.get("error_step")
            error_reason = payment_entity.get("error_reason")

            # Check if Order exists in our DB, or upsert it
            order_record = None
            if razorpay_order_id:
                order_record = db.query(Order).filter(Order.razorpay_order_id == razorpay_order_id).first()
                if not order_record:
                    # Event-order tolerance: Create order record if payment arrived before order sync
                    order_record = Order(
                        razorpay_order_id=razorpay_order_id,
                        amount=amount,
                        currency=currency,
                        status="paid" if payment_status == "captured" else "attempted",
                    )
                    db.add(order_record)
                    db.flush()
                else:
                    if payment_status == "captured":
                        order_record.status = "paid"
                    elif payment_status == "failed" and order_record.status != "paid":
                        order_record.status = "failed"

            # Check if Payment record already exists
            payment_record = db.query(Payment).filter(
                Payment.razorpay_payment_id == razorpay_payment_id
            ).first()

            if payment_record:
                payment_record.status = payment_status
                payment_record.amount = amount
                payment_record.currency = currency
                if method:
                    payment_record.method = method
                if bank:
                    payment_record.bank = bank
                if wallet:
                    payment_record.wallet = wallet
                if vpa:
                    payment_record.vpa = vpa
                if email:
                    payment_record.email = email
                if contact:
                    payment_record.contact = contact
                if error_code:
                    payment_record.error_code = error_code
                if error_description:
                    payment_record.error_description = error_description
                if error_source:
                    payment_record.error_source = error_source
                if error_step:
                    payment_record.error_step = error_step
                if error_reason:
                    payment_record.error_reason = error_reason
                payment_record.raw_payload = json.dumps(payment_entity)
            else:
                payment_record = Payment(
                    razorpay_payment_id=razorpay_payment_id,
                    razorpay_order_id=razorpay_order_id,
                    order_id=order_record.id if order_record else None,
                    amount=amount,
                    currency=currency,
                    status=payment_status,
                    method=method,
                    bank=bank,
                    wallet=wallet,
                    vpa=vpa,
                    email=email,
                    contact=contact,
                    error_code=error_code,
                    error_description=error_description,
                    error_source=error_source,
                    error_step=error_step,
                    error_reason=error_reason,
                    raw_payload=json.dumps(payment_entity),
                )
                db.add(payment_record)

        # 2. Process order payload if present (e.g. order.paid)
        if order_entity:
            rzp_order_id = order_entity.get("id")
            order_status = order_entity.get("status", "created")
            order_amount = order_entity.get("amount", 0)
            order_currency = order_entity.get("currency", "INR")
            order_receipt = order_entity.get("receipt")

            order_record = db.query(Order).filter(Order.razorpay_order_id == rzp_order_id).first()
            if order_record:
                order_record.status = order_status
                if order_receipt and not order_record.receipt:
                    order_record.receipt = order_receipt
            else:
                order_record = Order(
                    razorpay_order_id=rzp_order_id,
                    amount=order_amount,
                    currency=order_currency,
                    status=order_status,
                    receipt=order_receipt,
                )
                db.add(order_record)

        if event_record:
            event_record.status = "processed"
            event_record.processed_at = datetime.now(timezone.utc)

        db.commit()
        logger.info(f"Successfully processed webhook event {event_id} ({event_type})")

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing webhook event {event_id}: {str(e)}", exc_info=True)
        if event_record:
            event_record.status = "failed"
            event_record.error_message = str(e)
            db.commit()
    finally:
        db.close()