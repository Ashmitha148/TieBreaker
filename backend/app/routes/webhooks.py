from fastapi import APIRouter
router = APIRouter()
@router.get("/webhooks")
def list_webhooks():
    return {"webhooks": []}
