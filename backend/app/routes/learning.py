"""
TieBreaker Learning Loop
Surfaces analyst override patterns and triggers retraining recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import Counter
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Override, Decision

router = APIRouter()


@router.get("/learning/override-stats")
def get_override_stats(db: Session = Depends(get_db)):
    """
    Aggregate statistics on analyst overrides.
    Shows: total overrides, override rate, most common corrections, trend.
    """
    total_overrides = db.query(Override).count()
    total_decisions = db.query(Decision).count()
    override_rate = (total_overrides / total_decisions * 100) if total_decisions > 0 else 0

    # Most common override patterns (e.g., BLOCK → REVIEW)
    patterns = db.query(
        Override.original_action,
        Override.overridden_action,
        func.count(Override.id).label("count")
    ).group_by(
        Override.original_action,
        Override.overridden_action
    ).order_by(func.count(Override.id).desc()).all()

    # Recent trend (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_overrides = db.query(Override).filter(Override.created_at >= week_ago).count()

    return {
        "total_decisions": total_decisions,
        "total_overrides": total_overrides,
        "override_rate_percent": round(override_rate, 2),
        "recent_overrides_7d": recent_overrides,
        "top_override_patterns": [
            {
                "from": p.original_action,
                "to": p.overridden_action,
                "count": p.count,
            }
            for p in patterns[:5]
        ],
        "retraining_recommended": override_rate > 15.0,  # If >15% of decisions are overridden, model is drifting
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/learning/override-feedback")
def get_override_feedback(db: Session = Depends(get_db), limit: int = 50):
    """
    Raw override feedback for model retraining pipeline.
    Returns: original decision + override + feature snapshot.
    """
    overrides = db.query(Override).order_by(Override.created_at.desc()).limit(limit).all()

    feedback = []
    for ov in overrides:
        decision = db.query(Decision).filter(Decision.id == ov.decision_id).first()
        feedback.append({
            "transaction_id": ov.transaction_id,
            "original_action": ov.original_action,
            "overridden_action": ov.overridden_action,
            "reason": ov.reason,
            "analyst_id": ov.analyst_id,
            "created_at": ov.created_at.isoformat() if ov.created_at else None,
            "feature_snapshot": decision.feature_snapshot if decision else None,
            "model_version": decision.model_version if decision else None,
        })

    return {
        "feedback_count": len(feedback),
        "feedback": feedback,
    }


@router.post("/learning/trigger-retrain")
def trigger_retrain(db: Session = Depends(get_db)):
    """
    Mark that a retraining is needed. In production, this would queue a job.
    For the buildathon, it returns a report of what would be retrained.
    """
    stats = get_override_stats(db)

    if not stats["retraining_recommended"]:
        return {
            "status": "skipped",
            "reason": f"Override rate ({stats['override_rate_percent']}%) is below 15% threshold. No retraining needed.",
        }

    # Count feedback samples available
    feedback_count = db.query(Override).count()

    return {
        "status": "recommended",
        "reason": f"Override rate ({stats['override_rate_percent']}%) exceeds 15% threshold.",
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