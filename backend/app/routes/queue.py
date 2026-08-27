from fastapi import APIRouter
router = APIRouter()

@router.get("/queue")
def get_queue():
    return {"rankings": ["fraud_score", "expected_loss", "oracle"], "cases": []}