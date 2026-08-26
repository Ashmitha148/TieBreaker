
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Order, Payment
from ..schemas import PaymentResponse, PaymentVerifyRequest
from ..services.razorpay_service import verify_payment_signature

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.get("", response_model=list[PaymentResponse])
def list_payments(limit: int = 50, db: Session = Depends(get_db)):
    """
    Returns list of persisted payments/transactions for visibility in TieBreaker UI.
    """
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(limit).all()
    return payments


@router.post("/verify")
def verify_checkout_payment(verify_data: PaymentVerifyRequest, db: Session = Depends(get_db)):
    """
    Client-side checkout verification endpoint.
    Verifies the payment signature returned by Checkout.js using the server-side key secret.
    """
    if not settings.is_razorpay_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Razorpay credentials not configured on server",
        )

    is_valid = verify_payment_signature(
        razorpay_order_id=verify_data.razorpay_order_id,
        razorpay_payment_id=verify_data.razorpay_payment_id,
        razorpay_signature=verify_data.razorpay_signature,
        secret=settings.RAZORPAY_KEY_SECRET,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature",
        )

    order = db.query(Order).filter(Order.razorpay_order_id == verify_data.razorpay_order_id).first()
    if order:
        order.status = "paid"
        db.commit()

    return {
        "status": "success",
        "message": "Payment signature verified successfully",
        "razorpay_order_id": verify_data.razorpay_order_id,
        "razorpay_payment_id": verify_data.razorpay_payment_id,
    }