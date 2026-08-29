from fastapi import APIRouter

from ..config import settings

router = APIRouter()

CURRENT_CONFIG = {
    "FRAUD_LOSS_MULTIPLIER": 2.5,
    "FRICTION_COST_RATE": 0.05,
    "RESIDUAL_FRAUD_POST_3DS": 0.30,
    "ANALYST_HOUR_COST": 100.0,
    "DELAY_RISK_RATE": 0.15,
}


@router.get("/config")
def get_config():
    return {
        "is_configured": settings.is_razorpay_configured,
        "environment": settings.ENVIRONMENT,
        "is_test_mode": True,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID if settings.is_razorpay_configured else None,
        "current": CURRENT_CONFIG,
        "version": "1.0",
    }


@router.put("/config")
def update_config(config: dict):
    global CURRENT_CONFIG
    CURRENT_CONFIG.update(config)
    return {"status": "updated", "config": CURRENT_CONFIG, "version": "1.1"}
