from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..config import settings
from ..database import get_db
from ..models import Payment, Order
from ..schemas import PaymentResponse, PaymentVerifyRequest
from ..services.razorpay_service import verify_payment_signature

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


@router.post("/payments/verify")
def verify_payment(
    payload: PaymentVerifyRequest,
    db: Session = Depends(get_db),
):
    if not settings.is_razorpay_configured:
        raise HTTPException(
            status_code=503,
            detail="Razorpay credentials are not configured.",
        )

    is_valid = verify_payment_signature(
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
        secret=settings.RAZORPAY_KEY_SECRET,
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment signature",
        )

    order = db.query(Order).filter(Order.razorpay_order_id == payload.razorpay_order_id).first()
    if order:
        order.status = "paid"
        db.commit()

    return {
        "status": "success",
        "message": "Payment verified successfully",
        "razorpay_order_id": payload.razorpay_order_id,
        "razorpay_payment_id": payload.razorpay_payment_id,
    }

