import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Order
from ..schemas import OrderCreate, OrderResponse
from ..services.razorpay_service import RazorpayNotConfiguredError, create_order

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_new_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """
    Creates a real Razorpay Test Mode order and stores the order record in the database.
    Rejects with 503 if Razorpay credentials are not configured.
    """
    try:
        rzp_order = create_order(
            amount=order_in.amount,
            currency=order_in.currency,
            receipt=order_in.receipt,
            notes=order_in.notes,
        )
    except RazorpayNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Razorpay order creation failed: {e!s}",
        )

    # Persist the order in our database
    order_record = Order(
        razorpay_order_id=rzp_order["id"],
        amount=order_in.amount,
        currency=order_in.currency,
        status="created",
        receipt=rzp_order.get("receipt") or order_in.receipt,
        notes=json.dumps(order_in.notes) if order_in.notes else None,
    )
    db.add(order_record)
    db.commit()
    db.refresh(order_record)

    response = OrderResponse(
        id=order_record.id,
        razorpay_order_id=order_record.razorpay_order_id,
        amount=order_record.amount,
        currency=order_record.currency,
        status=order_record.status,
        receipt=order_record.receipt,
        key_id=settings.RAZORPAY_KEY_ID if settings.is_razorpay_configured else None,
        created_at=order_record.created_at,
    )
    return response


@router.get("", response_model=list[OrderResponse])
def list_orders(limit: int = 50, db: Session = Depends(get_db)):
    """Lists recent orders created in the database."""
    orders = db.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
    return [
        OrderResponse(
            id=o.id,
            razorpay_order_id=o.razorpay_order_id,
            amount=o.amount,
            currency=o.currency,
            status=o.status,
            receipt=o.receipt,
            key_id=settings.RAZORPAY_KEY_ID if settings.is_razorpay_configured else None,
            created_at=o.created_at,
        )
        for o in orders
    ]