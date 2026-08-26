from fastapi import APIRouter
router = APIRouter()
@router.get("/cost_config")
def get_cost_config():
    return {"cost_config": {}}
