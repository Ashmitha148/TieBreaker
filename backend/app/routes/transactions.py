from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

class TransactionBase(BaseModel):
    amount: float
    description: Optional[str] = None
    category: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

FAKE_DB: dict[int, Transaction] = {}
_next_id = 1

@router.get("/transactions", response_model=List[Transaction])
def list_transactions():
    return list(FAKE_DB.values())

@router.get("/transactions/{transaction_id}", response_model=Transaction)
def get_transaction(transaction_id: int):
    tx = FAKE_DB.get(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx

@router.post("/transactions", response_model=Transaction, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate):
    global _next_id
    tx = Transaction(id=_next_id, amount=payload.amount, description=payload.description, category=payload.category, created_at=datetime.utcnow())
    FAKE_DB[_next_id] = tx
    _next_id += 1
    return tx

@router.put("/transactions/{transaction_id}", response_model=Transaction)
def update_transaction(transaction_id: int, payload: TransactionCreate):
    if transaction_id not in FAKE_DB:
        raise HTTPException(status_code=404, detail="Transaction not found")
    existing = FAKE_DB[transaction_id]
    updated = existing.model_copy(update={"amount": payload.amount, "description": payload.description, "category": payload.category})
    FAKE_DB[transaction_id] = updated
    return updated

@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int):
    if transaction_id not in FAKE_DB:
        raise HTTPException(status_code=404, detail="Transaction not found")
    del FAKE_DB[transaction_id]
    return None
