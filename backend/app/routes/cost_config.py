from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict

from ..auth import verify_api_key
from ..database import get_db
from ..models import ConfigHistory
from ..services.strike_selector import DEFAULT_CONFIG

router = APIRouter()


@router.get("/cost-config")
def get_cost_config(db: Session = Depends(get_db)):
    """Get active cost configuration. Falls back to code defaults if no DB record."""
    latest = db.query(ConfigHistory).order_by(ConfigHistory.created_at.desc()).first()

    if latest:
        import json
        try:
            snapshot = json.loads(latest.config_snapshot)
        except Exception:
            snapshot = DEFAULT_CONFIG
    else:
        snapshot = DEFAULT_CONFIG

    return {
        "config": snapshot,
        "version": latest.version if latest else "1.0-default",
        "changed_by": latest.changed_by if latest else "system",
        "updated_at": latest.created_at.isoformat() if latest else None,
    }


@router.put("/cost-config")
def update_cost_config(
    config: Dict[str, float],
    db: Session = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    """Update cost configuration. Requires X-API-Key. Validates keys and creates audit history."""
    valid_keys = set(DEFAULT_CONFIG.keys())
    incoming_keys = set(config.keys())

    invalid = incoming_keys - valid_keys
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid config keys: {invalid}. Valid keys: {valid_keys}",
        )

    # Merge with defaults for any missing keys
    merged = {**DEFAULT_CONFIG, **config}

    import json
    history = ConfigHistory(
        config_snapshot=json.dumps(merged),
        version="1.1",  # In production, bump semver
        changed_by="api_user",
    )
    db.add(history)
    db.commit()

    return {"status": "updated", "config": merged, "version": history.version}
