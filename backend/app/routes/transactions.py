from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random

from ..database import get_db
from ..models import Decision, Override, AuditLog
from ..services.strike_selector import calculate_action_losses, threshold_baseline_decision
from ..ml.models import get_model_manager

router = APIRouter()


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    mgr = get_model_manager()
    decision = db.query(Decision).filter(Decision.transaction_id == transaction_id).first()

    if decision:
        record = {
            "amount": decision.amount,
            "ltv": decision.ltv,
            "fraud_prob": decision.fraud_prob,
            "fp_prob": decision.fp_prob,
            "velocity_1h": random.randint(1, 15),
            "velocity_24h": random.randint(5, 50),
            "device_change_flag": random.choice([0, 1]),
            "geo_mismatch_flag": random.choice([0, 1]),
            "is_cross_border": random.choice([0, 1]),
            "hour_of_day": random.randint(0, 23),
            "customer_tenure_days": random.randint(10, 2000),
            "customer_tx_count_30d": random.randint(1, 100),
            "customer_refund_rate": round(random.random(), 2),
            "merchant_category": random.choice(["Retail", "SaaS", "B2B", "Food"]),
        }
    else:
        if transaction_id == "TXN-COUNTER-001":
            record = {
                "amount": 450000, "ltv": 1200000, "fraud_prob": 0.72, "fp_prob": 0.35,
                "velocity_1h": 12, "velocity_24h": 45, "device_change_flag": 1,
                "geo_mismatch_flag": 1, "is_cross_border": 0, "hour_of_day": 14,
                "customer_tenure_days": 180, "customer_tx_count_30d": 25,
                "customer_refund_rate": 0.02, "merchant_category": "SaaS",
            }
        else:
            record = {
                "amount": random.choice([25000, 75000, 150000, 500000, 1200000]),
                "ltv": random.choice([50000, 200000, 600000, 1500000]),
                "fraud_prob": round(random.uniform(0.05, 0.95), 2),
                "fp_prob": round(random.uniform(0.02, 0.40), 2),
                "velocity_1h": random.randint(1, 15), "velocity_24h": random.randint(5, 50),
                "device_change_flag": random.choice([0, 1]),
                "geo_mismatch_flag": random.choice([0, 1]),
                "is_cross_border": random.choice([0, 1]),
                "hour_of_day": random.randint(0, 23),
                "customer_tenure_days": random.randint(10, 2000),
                "customer_tx_count_30d": random.randint(1, 100),
                "customer_refund_rate": round(random.random(), 2),
                "merchant_category": random.choice(["Retail", "SaaS", "B2B", "Food"]),
            }

    fraud_prob = mgr.predict_fraud_prob(record)
    fp_prob = mgr.predict_fp_prob(record)
    review_time = mgr.predict_review_time(record)
    record["fraud_prob"] = fraud_prob
    record["fp_prob"] = fp_prob

    result = calculate_action_losses(fraud_prob, fp_prob, record["amount"], record["ltv"])
    drivers = mgr.get_shap_drivers(record, top_n=3)
    baseline = threshold_baseline_decision(fraud_prob)
    override = db.query(Override).filter(Override.transaction_id == transaction_id).first()

    return {
        "transaction_id": transaction_id,
        "amount": record["amount"],
        "ltv": record["ltv"],
        "fraud_probability": fraud_prob,
        "fp_probability": fp_prob,
        "review_time_minutes": review_time,
        "recommended_action": result["recommended_action"],
        "baseline_action": baseline,
        "confidence_gap": result["confidence_gap"],
        "losses": result["losses"],
        "primary_reason": result["primary_reason"],
        "secondary_reason": result["secondary_reason"],
        "is_counterintuitive": result["is_counterintuitive"],
        "shap_drivers": drivers,
        "model_version": "2.0.0",
        "config_version": "1.0",
        "override": {
            "original_action": override.original_action,
            "overridden_action": override.overridden_action,
            "reason": override.reason,
            "analyst_id": override.analyst_id,
            "created_at": override.created_at.isoformat() if override.created_at else None,
        } if override else None,
    }


@router.post("/transactions/{transaction_id}/override")
def override_transaction(
    transaction_id: str,
    action: str,
    reason: str,
    analyst_id: str,
    db: Session = Depends(get_db),
):
    valid_actions = ["ALLOW", "VERIFY", "REVIEW", "BLOCK"]
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of {valid_actions}")

    decision = db.query(Decision).filter(Decision.transaction_id == transaction_id).first()
    if not decision:
        decision = Decision(
            transaction_id=transaction_id,
            fraud_prob=0.5,
            fp_prob=0.1,
            amount=100000,
            ltv=200000,
            recommended_action="REVIEW",
            baseline_action="REVIEW",
            savings_vs_baseline=0.0,
            model_version="2.0.0",
            config_version="1.0",
            is_counterintuitive=False,
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

    override = Override(
        decision_id=decision.id,
        transaction_id=transaction_id,
        original_action=decision.recommended_action,
        overridden_action=action,
        reason=reason,
        analyst_id=analyst_id,
    )
    db.add(override)

    audit = AuditLog(
        user=analyst_id,
        action="OVERRIDE",
        entity_type="Decision",
        entity_id=transaction_id,
        details=f"Overridden from {decision.recommended_action} to {action}. Reason: {reason}",
        model_version=decision.model_version,
        config_version=decision.config_version,
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "transaction_id": transaction_id,
        "original_action": decision.recommended_action,
        "overridden_action": action,
        "reason": reason,
        "analyst_id": analyst_id,
    }
