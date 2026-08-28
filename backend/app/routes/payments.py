from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import Payment
from ..schemas import PaymentResponse

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
