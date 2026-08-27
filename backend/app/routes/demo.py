from fastapi import APIRouter
from app.routes.transactions import get_transaction

router = APIRouter()

@router.get('/demo/counterintuitive')
def counterintuitive_demo():
    return get_transaction('TXN-COUNTER-001')
