"""
TieBreaker Learning Loop
Surfaces analyst override patterns and triggers retraining recommendations.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Override, Decision
from ..auth import verify_api_key

router = APIRouter()

RETRAIN_THRESHOLD_PERCENT = 15.0
RECENT_WINDOW_DAYS = 7
# FIXED: recent-window trigger is intentionally more sensitive than the
# all-time trigger, so a real drift spike this week isn't diluted into an
# average of months of stable decisions.
RECENT_RETRAIN_THRESHOLD_PERCENT = 10.0


def _compute_override_stats(db: Session) -> dict:
    total_overrides = db.query(Override).count()
    total_decisions = db.query(Decision).count()
    override_rate = (total_overrides / total_decisions * 100) if total_decisions > 0 else 0

    patterns = db.query(
        Override.original_action,
        Override.overridden_action,
        func.count(Override.id).label("pattern_count"),  # FIXED: renamed from "count"
    ).group_by(
        Override.original_action,
        Override.overridden_action
    ).order_by(func.count(Override.id).desc()).all()

    week_ago = datetime.utcnow() - timedelta(days=RECENT_WINDOW_DAYS)
    recent_overrides = db.query(Override).filter(Override.created_at >= week_ago).count()
    recent_decisions = db.query(Decision).filter(Decision.created_at >= week_ago).count()
    recent_override_rate = (recent_overrides / recent_decisions * 100) if recent_decisions > 0 else 0

    # FIXED: retraining now triggers on EITHER a sustained high all-time rate
    # OR a recent spike, instead of only the diluted all-time average.
    retraining_recommended = (
        override_rate > RETRAIN_THRESHOLD_PERCENT
        or recent_override_rate > RECENT_RETRAIN_THRESHOLD_PERCENT
    )
    trigger_reason = (
        "all_time" if override_rate > RETRAIN_THRESHOLD_PERCENT
        else "recent_spike" if recent_override_rate > RECENT_RETRAIN_THRESHOLD_PERCENT
        else None
    )

    return {
        "total_decisions": total_decisions,
        "total_overrides": total_overrides,
        "override_rate_percent": round(override_rate, 2),
        "recent_overrides_7d": recent_overrides,
        "recent_override_rate_percent": round(recent_override_rate, 2),
        "top_override_patterns": [
            {
                "from": p.original_action,
                "to": p.overridden_action,
                "count": p.pattern_count,
            }
            for p in patterns[:5]
        ],
        "retraining_recommended": retraining_recommended,
        "retraining_trigger_reason": trigger_reason,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/learning/override-stats")
def get_override_stats(db: Session = Depends(get_db), _api_key: str = Depends(verify_api_key)):
    """
    Aggregate statistics on analyst overrides.
    Shows: total overrides, override rate, most common corrections, trend.
    """
    return _compute_override_stats(db)


@router.get("/learning/override-feedback")
def get_override_feedback(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),  # FIXED: was unbounded
    _api_key: str = Depends(verify_api_key),
):
    """
    Raw override feedback for model retraining pipeline.
    Returns: original decision + override + feature snapshot.
    """
    # FIXED: single join instead of one Decision query per Override (N+1).
    rows = (
        db.query(Override, Decision)
        .outerjoin(Decision, Decision.id == Override.decision_id)
        .order_by(Override.created_at.desc())
        .limit(limit)
        .all()
    )

    feedback = [
        {
            "transaction_id": ov.transaction_id,
            "original_action": ov.original_action,
            "overridden_action": ov.overridden_action,
            "reason": ov.reason,
            "analyst_id": ov.analyst_id,
            "created_at": ov.created_at.isoformat() if ov.created_at else None,
            "feature_snapshot": decision.feature_snapshot if decision else None,
            "model_version": decision.model_version if decision else None,
        }
        for ov, decision in rows
    ]

    return {
        "feedback_count": len(feedback),
        "feedback": feedback,
    }


@router.post("/learning/trigger-retrain")
def trigger_retrain(db: Session = Depends(get_db), _api_key: str = Depends(verify_api_key)):
    """
    Mark that a retraining is needed. In production, this would queue a job.
    For the buildathon, it returns a report of what would be retrained —
    this endpoint does not actually retrain anything.
    """
    stats = _compute_override_stats(db)

    if not stats["retraining_recommended"]:
        return {
            "status": "skipped",
            "reason": (
                f"Override rate ({stats['override_rate_percent']}%) and recent "
                f"7-day rate ({stats['recent_override_rate_percent']}%) are both "
                f"below their thresholds. No retraining needed."
            ),
        }

    feedback_count = db.query(Override).count()

    return {
        "status": "recommended",
        "reason": (
            f"Triggered by {stats['retraining_trigger_reason']}: "
            f"all-time rate {stats['override_rate_percent']}%, "
            f"recent 7-day rate {stats['recent_override_rate_percent']}%."
        ),
        "training_data": {
            "fraud_model_samples": stats["total_decisions"],
            "fp_model_samples": feedback_count,
            "new_features_considered": [
                "merchant_category_embedding",
                "session_duration_seconds",
                "device_fingerprint_consistency",
                "payment_method_risk_score",
            ],
        },
        "next_steps": [
            "Collect 30 days of override feedback",
            "Retrain FP model with weighted samples (overrides = higher weight)",
            "A/B test new model against current in shadow mode",
            "Deploy if PR-AUC improves by >2%",
        ],
    }