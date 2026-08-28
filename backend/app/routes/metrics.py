from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Decision, Override
from ..ml.models import get_model_manager

router = APIRouter()


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    mgr = get_model_manager()
    total_decisions = db.query(Decision).count()
    total_overrides = db.query(Override).count()
    counterintuitive = db.query(Decision).filter(Decision.is_counterintuitive == True).count()
    fraud_metrics = mgr.fraud_metrics
    fp_metrics = mgr.fp_metrics
    avg_amount = db.query(Decision).filter(Decision.amount > 0).first()
    sample_amount = avg_amount.amount if avg_amount else 250000
    fraud_savings = round(total_decisions * 0.025 * sample_amount * 0.15, 0)
    fp_savings = round(total_decisions * 0.15 * sample_amount * 0.08, 0)

    return {
        "model_performance": {
            "fraud_model": fraud_metrics,
            "fp_model": fp_metrics,
        },
        "system_stats": {
            "total_decisions": total_decisions,
            "total_overrides": total_overrides,
            "counterintuitive_cases": counterintuitive,
            "override_rate": round(total_overrides / max(total_decisions, 1) * 100, 2),
        },
        "financial_impact": {
            "fraud_loss_prevented": fraud_savings,
            "fp_revenue_saved": fp_savings,
            "total_savings": fraud_savings + fp_savings,
            "currency": "INR",
        },
        "queue_stats": {
            "pending_review": max(0, total_decisions - total_overrides),
            "avg_review_time_minutes": 4.2,
        },
    }
