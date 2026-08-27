from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..routes.transactions import get_transaction
from ..database import get_db

router = APIRouter()

@router.get('/demo/counterintuitive')
def get_counterintuitive(db: Session = Depends(get_db)):
    tx_id = 'TXN-COUNTER-001'
    result = get_transaction(tx_id, db)
    result['decision']['is_counterintuitive'] = True
    return result
