from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Decision, Override

router = APIRouter()


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    total_decisions = db.query(Decision).count()
    total_overrides = db.query(Override).count()

    # Action distribution
    action_counts = (
        db.query(Decision.recommended_action, func.count(Decision.id))
        .group_by(Decision.recommended_action)
        .all()
    )
    action_distribution = {action: count for action, count in action_counts}

    # Counterintuitive decisions
    counterintuitive = db.query(Decision).filter(Decision.is_counterintuitive == True).count()

    # Recent decisions (last 24h)
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_decisions = db.query(Decision).filter(Decision.created_at >= recent_cutoff).count()

    # Average savings
    avg_savings = db.query(func.avg(Decision.savings_vs_baseline)).scalar() or 0

    # Override rate
    override_rate = (total_overrides / total_decisions * 100) if total_decisions > 0 else 0

    return {
        "total_decisions": total_decisions,
        "total_overrides": total_overrides,
        "recent_decisions_24h": recent_decisions,
        "action_distribution": action_distribution,
        "counterintuitive_count": counterintuitive,
        "average_savings_vs_baseline_inr": round(float(avg_savings), 2),
        "override_rate_percent": round(override_rate, 2),
        "timestamp": datetime.utcnow().isoformat(),
    }