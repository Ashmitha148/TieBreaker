from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order
from ..schemas import OrderCreate, OrderResponse
from ..services.razorpay_service import create_order, RazorpayNotConfiguredError
from ..config import settings

router = APIRouter()


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return orders


@router.post("/orders", response_model=OrderResponse)
def create_new_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    try:
        rzp_order = create_order(
            amount=order_in.amount,
            currency=order_in.currency,
            receipt=order_in.receipt,
            notes=order_in.notes,
        )
    except RazorpayNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))

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
        "id": db_order.id,
        "razorpay_order_id": db_order.razorpay_order_id,
        "amount": db_order.amount,
        "currency": db_order.currency,
        "status": db_order.status,
        "receipt": db_order.receipt,
        "key_id": settings.RAZORPAY_KEY_ID,
        "created_at": db_order.created_at,
    }