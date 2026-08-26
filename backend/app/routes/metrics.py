from fastapi import APIRouter
router = APIRouter()
@router.get("/metrics")
def get_metrics():
    return {"status": "ok", "data": {}}
