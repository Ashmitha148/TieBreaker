from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..config import settings
from ..database import get_db
from ..models import Payment, Order, Decision
from ..schemas import PaymentResponse, PaymentVerifyRequest, OrderCreate
from ..services.razorpay_service import verify_payment_signature, create_order, RazorpayNotConfiguredError
from ..ml.predictor import predict_transaction

router = APIRouter()


@router.get("/payments", response_model=list[PaymentResponse])
def list_payments(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    method: Optional[str] = Query(None, description="Filter by payment method"),
    limit: int = Query(50, ge=1, le=200),
):
    query = db.query(Payment).order_by(Payment.created_at.desc())

    if status:
        query = query.filter(Payment.status.ilike(status))
    if method:
        query = query.filter(Payment.method.ilike(method))

    return query.limit(limit).all()


@router.post("/payment/create-order", status_code=201)
def create_payment_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
):
    """
    Create a real Razorpay TEST MODE order and return order_id + key_id
    so the frontend can open the Razorpay checkout modal.
    Amount must be in paise (INR * 100).
    """
    if not settings.is_razorpay_configured:
        raise HTTPException(
            status_code=503,
            detail="Razorpay credentials are not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env.",
        )

    try:
        rzp_order = create_order(
            amount=order_in.amount,
            currency=order_in.currency,
            receipt=order_in.receipt,
            notes=order_in.notes,
        )
    except RazorpayNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Persist the order in DB
    db_order = Order(
        razorpay_order_id=rzp_order["id"],
        amount=order_in.amount,
        currency=order_in.currency,
        status=rzp_order.get("status", "created"),
        receipt=order_in.receipt,
        notes=str(order_in.notes) if order_in.notes else None,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    return {
        "order_id": rzp_order["id"],
        "amount": rzp_order["amount"],
        "currency": rzp_order["currency"],
        "key_id": settings.RAZORPAY_KEY_ID,
        "receipt": rzp_order.get("receipt"),
        "status": rzp_order.get("status"),
    }


@router.post("/payment/verify")
def verify_payment_endpoint(
    payload: PaymentVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Verify the Razorpay payment signature (mandatory), then run the
    transaction through the existing fraud/FP risk-scoring pipeline.
    """
    if not settings.is_razorpay_configured:
        raise HTTPException(
            status_code=503,
            detail="Razorpay credentials are not configured.",
        )

    # Step 1: Mandatory signature verification — HMAC-SHA256 of "order_id|payment_id"
    is_valid = verify_payment_signature(
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
        secret=settings.RAZORPAY_KEY_SECRET,
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment signature — tampering detected.",
        )

    # Step 2: Look up the order to get amount + link payment
        # Step 2: Look up the order to get amount + link payment
    try:
        order = db.query(Order).filter(
            Order.razorpay_order_id == payload.razorpay_order_id
        ).first()
        amount_in_rupees = (order.amount / 100.0) if order else 0.0

        record = {
            "TransactionAmt": amount_in_rupees,
            "amount": amount_in_rupees,
            "hour_of_day": 12,
            "day_of_week": 0,
            "device_change_flag": 0,
            "geo_mismatch_flag": 0,
            "is_cross_border": 0,
            "customer_tenure_days": 365,
            "customer_tx_count_30d": 10,
            "customer_refund_rate": 0.0,
            "velocity_1h": 0,
            "velocity_24h": 0,
        }
        prediction = predict_transaction(record)
        fraud_prob = prediction["fraud_probability"]
        fp_prob = prediction["fp_probability"]

        if fraud_prob > 0.7:
            recommended_action = "BLOCK"
        elif fraud_prob > 0.5:
            recommended_action = "REVIEW"
        elif fraud_prob > 0.3:
            recommended_action = "VERIFY"
        else:
            recommended_action = "ALLOW"

        decision = Decision(
            transaction_id=payload.razorpay_payment_id,
            fraud_prob=fraud_prob,
            fp_prob=fp_prob,
            amount=amount_in_rupees,
            ltv=0.0,
            recommended_action=recommended_action,
            baseline_action="ALLOW",
            savings_vs_baseline=0.0,
            model_version=prediction.get("model_version", "unloaded"),
            config_version="1.0",
            is_counterintuitive=(recommended_action == "REVIEW" and fraud_prob > 0.5),
        )
        db.add(decision)

        if order:
            order.status = "paid"

        payment = Payment(
            razorpay_payment_id=payload.razorpay_payment_id,
            razorpay_order_id=payload.razorpay_order_id,
            order_id=order.id if order else None,
            amount=order.amount if order else 0,
            currency=order.currency if order else "INR",
            status="captured",
        )
        db.add(payment)
        db.commit()

        return {
            "status": "success",
            "message": "Payment verified successfully",
            "razorpay_order_id": payload.razorpay_order_id,
            "razorpay_payment_id": payload.razorpay_payment_id,
            "transaction_id": payload.razorpay_payment_id,
            "amount": amount_in_rupees,
            "recommended_action": recommended_action,
            "fraud_probability": fraud_prob,
            "fp_probability": fp_prob,
            "is_counterintuitive": decision.is_counterintuitive,
        }
    except Exception as e:
        db.rollback()
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")