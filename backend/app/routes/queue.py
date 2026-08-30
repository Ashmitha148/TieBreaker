from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import random

from ..database import get_db
from ..models import Decision
from ..services.strike_selector import calculate_action_losses

router = APIRouter()


def _compute_impact_score(decision: Decision) -> float:
    losses = calculate_action_losses(
        fraud_prob=decision.fraud_prob,
        fp_prob=decision.fp_prob,
        amount=decision.amount,
        ltv=decision.ltv,
    )
    allow_loss = losses["losses"]["ALLOW"]
    review_loss = losses["losses"]["REVIEW"]
    review_time = 4.2
    impact = (allow_loss - review_loss) / review_time
    return round(impact, 2)


@router.get("/queue")
def get_queue(db: Session = Depends(get_db), limit: int = 50, min_fraud_prob: Optional[float] = None):
    query = db.query(Decision).order_by(Decision.fraud_prob.desc())
    if min_fraud_prob is not None:
        query = query.filter(Decision.fraud_prob >= min_fraud_prob)
    decisions = query.limit(limit).all()

    if not decisions:
        demo_cases = []
        # Overgenerate when a min_fraud_prob filter is active so filtering
        # still leaves a reasonable number of cases.
        pool_size = min(limit * 3, 150) if min_fraud_prob is not None else min(limit, 50)
        for i in range(pool_size):
            fraud_p = round(random.uniform(0.1, 0.95), 2)
            if min_fraud_prob is not None and fraud_p < min_fraud_prob:
                continue
            fp_p = round(random.uniform(0.02, 0.25), 2)
            amt = random.choice([25000, 50000, 120000, 350000, 800000, 1500000])
            ltv = round(amt * random.uniform(0.5, 3.0), 0)
            losses = calculate_action_losses(fraud_p, fp_p, amt, ltv)
            impact = (losses["losses"]["ALLOW"] - losses["losses"]["REVIEW"]) / 4.2
            demo_cases.append({
                "rank": 0,
                "transaction_id": f"TXN-DEMO-{i+1:03d}",
                "amount": amt,
                "fraud_probability": fraud_p,
                "recommended_action": losses["recommended_action"],
                "expected_loss_allow": losses["losses"]["ALLOW"],
                "expected_loss_review": losses["losses"]["REVIEW"],
                "impact_score": round(impact, 2),
                "is_counterintuitive": losses["is_counterintuitive"],
                "reason": losses["primary_reason"],
            })
            if min_fraud_prob is None and len(demo_cases) >= limit:
                break
        demo_cases.sort(key=lambda c: c["impact_score"], reverse=True)
        demo_cases = demo_cases[:limit]
        for i, c in enumerate(demo_cases, 1):
            c["rank"] = i
        return {"cases": demo_cases, "total": len(demo_cases), "source": "demo"}

    cases = []
    for rank, d in enumerate(decisions, 1):
        losses = calculate_action_losses(d.fraud_prob, d.fp_prob, d.amount, d.ltv)
        impact = _compute_impact_score(d)
        cases.append({
            "rank": rank,
            "transaction_id": d.transaction_id,
            "amount": d.amount,
            "fraud_probability": d.fraud_prob,
            "recommended_action": d.recommended_action,
            "expected_loss_allow": losses["losses"]["ALLOW"],
            "expected_loss_review": losses["losses"]["REVIEW"],
            "impact_score": impact,
            "is_counterintuitive": d.is_counterintuitive,
            "reason": losses["primary_reason"],
        })
    cases.sort(key=lambda x: x["impact_score"], reverse=True)
    for i, c in enumerate(cases, 1):
        c["rank"] = i
    return {"cases": cases, "total": len(cases), "source": "database"}