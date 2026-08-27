from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Payment
from ..schemas import PaymentResponse

router = APIRouter()


@router.get("/payments", response_model=list[PaymentResponse])
def list_payments(db: Session = Depends(get_db)):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(50).all()
    return payments