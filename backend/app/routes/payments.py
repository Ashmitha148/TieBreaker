from fastapi import APIRouter
router = APIRouter()
@router.get("/payments")
def list_payments():
    return {"payments": []}
