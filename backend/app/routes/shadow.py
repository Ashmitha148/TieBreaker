"""
Shadow scoring route — monitoring only.

Scores a transaction through the shadow (candidate) fraud model alongside the
primary model so we can measure drift between the deployed and candidate models.
The shadow score is persisted to the database for historical comparison and
**never** influences the live fraud decision.

POST /api/shadow-score        — score once, persist, return both scores (+ drift)
GET  /api/shadow-comparison   — recent shadow vs primary history + drift stats
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import verify_api_key
from ..database import get_db
from ..models import ShadowPrediction

router = APIRouter()

# backend/app/routes/shadow.py -> resolved parents[1] == backend/app
ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts"
SHADOW_PATH = ARTIFACTS_DIR / "fraud_model_shadow.joblib"


def _load_shadow():
    """Return (model, features) or (None, None) when the artifact is missing."""
    if not SHADOW_PATH.exists():
        return None, None
    try:
        artifact = joblib.load(SHADOW_PATH)
        model = artifact.get("model")
        features = artifact.get("features", []) or []
        if model is None or not features:
            return None, None
        return model, features
    except Exception:
        return None, None


@router.post("/shadow-score")
def shadow_score(
    payload: dict,
    _api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Run the shadow (candidate) fraud model on a transaction and persist the
    comparison. The returned ``decision`` is whatever the caller supplied —
    the shadow score does NOT affect the primary decision path.
    """
    primary = float(payload.get("fraud_probability", 0.0))
    transaction_id = str(payload.get("transaction_id") or "").strip()
    recommended_action = payload.get("recommended_action", "ALLOW")

    model, features = _load_shadow()
    shadow: Optional[float] = None
    if model is not None:
        try:
            X = [[float(payload.get(f, 0.0)) for f in features]]
            shadow = round(float(model.predict_proba(X)[0][1]), 4)
        except Exception:
            shadow = None

    delta = round(shadow - primary, 4) if shadow is not None else None

    record = ShadowPrediction(
        transaction_id=transaction_id or None,
        primary_score=primary,
        shadow_score=shadow,
        delta=delta,
        recommended_action=str(recommended_action),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "transaction_id": transaction_id or str(record.id),
        "primary_score": primary,
        "shadow_score": shadow,
        "delta": delta,
        "decision": recommended_action,
        "shadow_available": shadow is not None,
        "record_id": record.id,
        "note": "Shadow score is for monitoring only and does NOT affect the decision.",
    }


@router.get("/shadow-comparison")
def shadow_comparison(
    limit: int = Query(default=100, ge=1, le=1000),
    _api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Historical shadow-vs-primary comparison persisted by POST /api/shadow-score.

    Returns the most recent ``limit`` rows plus aggregate drift statistics:
    mean primary score, mean shadow score, mean absolute delta, and the share
    of records where the shadow score would flip the 0.5 decision threshold.
    """
    rows = (
        db.query(ShadowPrediction)
        .order_by(ShadowPrediction.created_at.desc())
        .limit(limit)
        .all()
    )
    recent = [
        {
            "id": r.id,
            "transaction_id": r.transaction_id,
            "primary_score": r.primary_score,
            "shadow_score": r.shadow_score,
            "delta": r.delta,
            "action": r.recommended_action,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    scored = [r for r in rows if r.shadow_score is not None]
    if scored:
        primary = [r.primary_score for r in scored]
        shadow = [r.shadow_score for r in scored]
        deltas = [r.delta for r in scored if r.delta is not None]
        flips = sum(1 for p, s in zip(primary, shadow) if (p >= 0.5) != (s >= 0.5))
        summary = {
            "sampled": len(scored),
            "primary_mean": round(sum(primary) / len(primary), 4),
            "shadow_mean": round(sum(shadow) / len(shadow), 4),
            "mean_abs_delta": round(sum(abs(d) for d in deltas) / len(deltas), 4) if deltas else None,
            "flip_count": flips,
            "flip_rate": round(flips / len(scored), 4),
        }
    else:
        summary = {
            "sampled": 0,
            "primary_mean": None,
            "shadow_mean": None,
            "mean_abs_delta": None,
            "flip_count": 0,
            "flip_rate": 0.0,
        }

    model, features = _load_shadow()
    return {
        "status": "ok",
        "shadow_model_loaded": model is not None,
        "shadow_features": features if features else [],
        "summary": summary,
        "recent": recent,
    }