from fastapi import APIRouter
router = APIRouter()
@router.get("/audit")
def get_audit_logs():
    return {"audit_logs": []}
