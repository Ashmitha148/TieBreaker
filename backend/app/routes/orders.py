from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Decision
from ..schemas import OrderCreate, OrderResponse
from ..services.razorpay_service import create_order, RazorpayNotConfiguredError
from ..config import settings
from ..ml.predictor import predict_transaction

router = APIRouter()


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return orders


@router.post("/create-order")
def create_new_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """
    Create a Razorpay order, run ML fraud/FP prediction, and return
the order_id along with the decision.
    """
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

    # Build a minimal record for ML prediction from order data
    record = {
        "TransactionAmt": order_in.amount / 100.0,  # Razorpay amount is in paise
        "amount": order_in.amount / 100.0,
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

    # Determine recommended action based on fraud probability
    if fraud_prob > 0.7:
        recommended_action = "BLOCK"
        requires_3ds = True
    elif fraud_prob > 0.5:
        recommended_action = "REVIEW"
        requires_3ds = True
    elif fraud_prob > 0.3:
        recommended_action = "VERIFY"
        requires_3ds = False
    else:
        recommended_action = "ALLOW"
        requires_3ds = False

    # Persist decision
    decision = Decision(
        transaction_id=rzp_order["id"],
        fraud_prob=fraud_prob,
        fp_prob=fp_prob,
        amount=order_in.amount / 100.0,
        ltv=0.0,
        recommended_action=recommended_action,
        baseline_action="ALLOW",
        savings_vs_baseline=0.0,
        model_version=prediction.get("model_version", "unloaded"),
        config_version="1.0",
        is_counterintuitive=False,
    )
    db.add(decision)
    db.commit()

    return {
        "order_id": rzp_order["id"],
        "decision": recommended_action,
        "fraud_prob": fraud_prob,
        "fp_prob": fp_prob,
        "recommended_action": recommended_action,
        "requires_3ds": requires_3ds,
        "key_id": settings.RAZORPAY_KEY_ID,
        "amount": db_order.amount,
        "currency": db_order.currency,
        "status": db_order.status,
        "created_at": db_order.created_at,
    }
