from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import verify_api_key
from ..config import settings

router = APIRouter()

CURRENT_CONFIG = {
    "FRAUD_LOSS_MULTIPLIER": 2.5,
    "FRICTION_COST_RATE": 0.05,
    "RESIDUAL_FRAUD_POST_3DS": 0.30,
    "ANALYST_HOUR_COST": 100.0,
    "DELAY_RISK_RATE": 0.15,
}


def _is_razorpay_configured() -> bool:
    return getattr(settings, "is_razorpay_configured", False)


@router.get("/config")
def get_config():
    return {
        "is_configured": _is_razorpay_configured(),
        "environment": settings.ENVIRONMENT,
        "is_test_mode": True,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID if _is_razorpay_configured() else None,
        "current": CURRENT_CONFIG,
        "version": "1.0",
    }


class ConfigUpdateRequest(BaseModel):
    """Whitelisted, typed update payload for PUT /api/config."""
    FRAUD_LOSS_MULTIPLIER: float | None = None
    FRICTION_COST_RATE: float | None = None
    RESIDUAL_FRAUD_POST_3DS: float | None = None
    ANALYST_HOUR_COST: float | None = None
    DELAY_RISK_RATE: float | None = None


@router.put("/config")
def update_config(config: ConfigUpdateRequest, _api_key: str = Depends(verify_api_key)):
    """Update runtime config. Requires X-API-Key; only whitelisted keys accepted."""
    global CURRENT_CONFIG
    updates = {k: v for k, v in config.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid config keys provided.")
    CURRENT_CONFIG.update(updates)
    return {"status": "updated", "config": CURRENT_CONFIG, "version": "1.1"}
