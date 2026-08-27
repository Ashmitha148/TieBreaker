from fastapi import APIRouter
router = APIRouter()

@router.get("/cost-config")
def get_cost_config():
    return {
        "FRAUD_LOSS_MULTIPLIER": 2.5,
        "FRICTION_COST_RATE": 0.05,
        "RESIDUAL_FRAUD_POST_3DS": 0.30,
        "ANALYST_HOUR_COST": 100.0,
        "DELAY_RISK_RATE": 0.15
    }

@router.put("/cost-config")
def update_cost_config(config: dict):
    return {"status": "updated", "config": config}