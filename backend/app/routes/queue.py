from fastapi import APIRouter
router = APIRouter()
@router.get("/queue")
def get_queue():
    return {"queue": []}
