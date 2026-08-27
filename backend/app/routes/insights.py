from fastapi import APIRouter
router = APIRouter()

@router.get("/insights")
def get_insights():
    return {"before": {}, "after": {}, "message": "Override Learner insights"}