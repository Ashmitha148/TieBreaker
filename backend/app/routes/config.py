from fastapi import APIRouter
router = APIRouter()
@router.get("/config")
def get_config():
    return {"config": {}}
