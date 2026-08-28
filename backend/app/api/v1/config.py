from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session, get_current_analyst
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas import CostConfig, ConfigResponse, ConfigUpdateResponse
from app.services import get_strike_engine, get_audit_service

logger = get_logger(__name__)
router = APIRouter(prefix="/config", tags=["Config"])


@router.get("", response_model=ConfigResponse)
def get_config():
    engine = get_strike_engine()
    return {
        "is_configured": settings.is_razorpay_configured,
        "environment": settings.ENVIRONMENT,
        "is_test_mode": settings.is_razorpay_configured and "test" in settings.RAZORPAY_KEY_ID,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID[:12] + "..." if settings.is_razorpay_configured else None,
        "current": engine.get_config(),
        "version": "2.1.0",
    }


@router.put("", response_model=ConfigUpdateResponse)
def update_config(
    config: CostConfig,
    analyst_id: str = Depends(get_current_analyst),
    db: Session = Depends(get_db_session),
):
    engine = get_strike_engine()
    new_config = config.model_dump()
    engine.update_config(new_config)
    
    audit = get_audit_service()
    audit.log(
        db=db,
        user_id=analyst_id,
        action="CONFIG_CHANGE",
        entity_type="CostConfig",
        entity_id="global",
        details=f"Updated cost config: {new_config}",
    )
    
    return {
        "status": "updated",
        "config": engine.get_config(),
        "version": "2.1.1",
    }