from fastapi import APIRouter
router = APIRouter()
@router.get("/demo/counterintuitive")
def counterintuitive_demo():
    return {"message": "demo endpoint"}
