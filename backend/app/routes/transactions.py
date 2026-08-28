from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import random
import uuid
import numpy as np

from ..database import get_db
from ..models import Decision, Override, AuditLog
from ..services.strike_selector import calculate_action_losses, threshold_baseline_decision
from ..ml.predictor import predict_transaction
from ..ml.models import get_model_manager
from ..config import settings

router = APIRouter()


MERCHANT_PROFILES = {
    "Retail": {"avg_amount": 45000, "ltv_base": 80000},
    "SaaS": {"avg_amount": 150000, "ltv_base": 600000},
    "B2B": {"avg_amount": 500000, "ltv_base": 2000000},
    "Food": {"avg_amount": 25000, "ltv_base": 40000},
    "Travel": {"avg_amount": 350000, "ltv_base": 500000},
    "EdTech": {"avg_amount": 120000, "ltv_base": 300000},
}


def _generate_new_record(transaction_id: str, merchant_category: str = None) -> dict:
    """Generate a realistic synthetic record for demo/seed ONLY."""
    if merchant_category is None:
        merchant_category = random.choice(list(MERCHANT_PROFILES.keys()))

    profile = MERCHANT_PROFILES[merchant_category]
    amount = max(1000, int(random.gauss(profile["avg_amount"], profile["avg_amount"] * 0.4)))
    tenure = random.randint(7, 1500)
    ltv = int(profile["ltv_base"] * (0.5 + tenure / 2000) * random.uniform(0.8, 1.5))

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "ltv": ltv,
        "velocity_1h": random.randint(1, 20),
        "velocity_24h": random.randint(5, 80),
        "device_change_flag": random.choice([0, 1]),
        "geo_mismatch_flag": random.choice([0, 1]),
        "is_cross_border": random.choice([0, 1]),
        "hour_of_day": random.randint(0, 23),
        "customer_tenure_days": tenure,
        "customer_tx_count_30d": random.randint(1, 120),
        "customer_refund_rate": round(random.random(), 2),
        "merchant_category": merchant_category,
        "payment_method": random.choice(["upi", "card", "netbanking", "wallet"]),
    }


@router.post("/transactions")
def create_transaction(
    transaction_id: str,
    amount: float,
    ltv: float,
    merchant_category: str = "Retail",
    velocity_1h: int = 0,
    velocity_24h: int = 0,
    device_change_flag: int = 0,
    geo_mismatch_flag: int = 0,
    is_cross_border: int = 0,
    hour_of_day: int = 12,
    customer_tenure_days: int = 365,
    customer_tx_count_30d: int = 10,
    customer_refund_rate: float = 0.0,
    payment_method: str = "upi",
    db: Session = Depends(get_db),
):
    """
    Ingest a REAL transaction (from Razorpay webhook, CSV upload, or test mode).
    Runs dual-model inference and persists the decision.
    """
    record = {
        "transaction_id": transaction_id,
        "amount": amount,
        "ltv": ltv,
        "velocity_1h": velocity_1h,
        "velocity_24h": velocity_24h,
        "device_change_flag": device_change_flag,
        "geo_mismatch_flag": geo_mismatch_flag,
        "is_cross_border": is_cross_border,
        "hour_of_day": hour_of_day,
        "customer_tenure_days": customer_tenure_days,
        "customer_tx_count_30d": customer_tx_count_30d,
        "customer_refund_rate": customer_refund_rate,
        "merchant_category": merchant_category,
        "payment_method": payment_method,
    }

    prediction = predict_transaction(record)
    fraud_prob = prediction["fraud_probability"]
    fp_prob = prediction["fp_probability"]
    record["fraud_prob"] = fraud_prob
    record["fp_prob"] = fp_prob

    result = calculate_action_losses(fraud_prob, fp_prob, amount, ltv)
    baseline = threshold_baseline_decision(fraud_prob)

    savings = round(
        result["losses"].get(baseline, result["losses"]["BLOCK"]) - result["losses"][result["recommended_action"]],
        2,
    )

    decision = Decision(
        transaction_id=transaction_id,
        fraud_prob=fraud_prob,
        fp_prob=fp_prob,
        amount=amount,
        ltv=ltv,
        merchant_category=merchant_category,
        recommended_action=result["recommended_action"],
        baseline_action=baseline,
        savings_vs_baseline=savings,
        model_version="2.0.0",
        config_version="1.0",
        is_counterintuitive=result["is_counterintuitive"],
        feature_snapshot=json.dumps(record),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    return {
        "transaction_id": transaction_id,
        "recommended_action": result["recommended_action"],
        "baseline_action": baseline,
        "fraud_probability": fraud_prob,
        "fp_probability": fp_prob,
        "savings_vs_baseline": savings,
        "is_counterintuitive": result["is_counterintuitive"],
    }


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """
    Get full decision payload for a transaction.
    In production: returns 404 if not found (no auto-generation).
    In development: auto-generates synthetic data for demo purposes.
    """
    decision = db.query(Decision).filter(Decision.transaction_id == transaction_id).first()

    if decision:
        # Use stored snapshot for consistent features
        if decision.feature_snapshot:
            record = json.loads(decision.feature_snapshot)
        else:
            record = {
                "transaction_id": transaction_id,
                "amount": decision.amount,
                "ltv": decision.ltv,
                "merchant_category": decision.merchant_category or "Retail",
                "velocity_1h": 0,
                "velocity_24h": 0,
                "device_change_flag": 0,
                "geo_mismatch_flag": 0,
                "is_cross_border": 0,
                "hour_of_day": 12,
                "customer_tenure_days": 365,
                "customer_tx_count_30d": 10,
                "customer_refund_rate": 0.0,
                "payment_method": "upi",
            }

        fraud_prob = decision.fraud_prob
        fp_prob = decision.fp_prob

        mgr = get_model_manager()
        drivers = mgr.get_shap_drivers(record, top_n=3)

        result = calculate_action_losses(fraud_prob, fp_prob, decision.amount, decision.ltv)
        baseline = threshold_baseline_decision(fraud_prob)

    else:
        # PRODUCTION: Do NOT auto-generate fake data
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=404,
                detail=f"Transaction {transaction_id} not found. Use POST /api/transactions to ingest real data.",
            )

        # DEVELOPMENT ONLY: generate synthetic demo data
        record = _generate_new_record(transaction_id)
        prediction = predict_transaction(record)

        fraud_prob = prediction["fraud_probability"]
        fp_prob = prediction["fp_probability"]
        record["fraud_prob"] = fraud_prob
        record["fp_prob"] = fp_prob

        result = calculate_action_losses(fraud_prob, fp_prob, record["amount"], record["ltv"])
        baseline = threshold_baseline_decision(fraud_prob)

        savings = round(
            result["losses"].get(baseline, result["losses"]["BLOCK"]) - result["losses"][result["recommended_action"]],
            2,
        )

        decision = Decision(
            transaction_id=transaction_id,
            fraud_prob=fraud_prob,
            fp_prob=fp_prob,
            amount=record["amount"],
            ltv=record["ltv"],
            merchant_category=record.get("merchant_category"),
            recommended_action=result["recommended_action"],
            baseline_action=baseline,
            savings_vs_baseline=savings,
            model_version="2.0.0",
            config_version="1.0",
            is_counterintuitive=result["is_counterintuitive"],
            feature_snapshot=json.dumps(record),
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        drivers = prediction["shap_drivers"]

    override = db.query(Override).filter(Override.transaction_id == transaction_id).first()

    return {
        "transaction_id": transaction_id,
        "amount": decision.amount,
        "ltv": decision.ltv,
        "merchant_category": decision.merchant_category or record.get("merchant_category"),
        "fraud_probability": fraud_prob,
        "fp_probability": fp_prob,
        "recommended_action": result["recommended_action"],
        "baseline_action": baseline,
        "confidence_gap": result["confidence_gap"],
        "losses": result["losses"],
        "primary_reason": result["primary_reason"],
        "secondary_reason": result["secondary_reason"],
        "is_counterintuitive": result["is_counterintuitive"],
        "shap_drivers": drivers,
        "model_version": decision.model_version,
        "config_version": decision.config_version,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
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
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found.",
        )

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


@router.get("/transactions/{transaction_id}/shap-chart")
def get_shap_chart(transaction_id: str, db: Session = Depends(get_db)):
    """Generate a SHAP waterfall chart PNG for a transaction."""
    import io
    import base64
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap

    decision = db.query(Decision).filter(Decision.transaction_id == transaction_id).first()

    if not decision or not decision.feature_snapshot:
        raise HTTPException(
            status_code=404,
            detail="Transaction or feature snapshot not found",
        )

    record = json.loads(decision.feature_snapshot)
    mgr = get_model_manager()

    features = []
    for f in mgr.fraud_features:
        if f == "merchant_category_encoded":
            features.append(
                {
                    "Retail": 0,
                    "SaaS": 1,
                    "B2B": 2,
                    "Food": 3,
                }.get(record.get("merchant_category", "Retail"), 0)
            )
        else:
            features.append(record.get(f, 0))

    if mgr.fraud_model is None or not shap:
        raise HTTPException(status_code=503, detail="SHAP not available")

    explainer = shap.TreeExplainer(mgr.fraud_model)
    sv = explainer.shap_values([features])

    if isinstance(sv, list):
        sv = sv[1][0]

    plt.figure(figsize=(10, 6))

    shap.waterfall_plot(
        shap.Explanation(
            values=np.array(sv),
            base_values=(
                explainer.expected_value[1]
                if isinstance(explainer.expected_value, list)
                else explainer.expected_value
            ),
            data=np.array(features),
            feature_names=mgr.fraud_features,
        ),
        max_display=10,
        show=False,
    )

    plt.title(f"SHAP: {transaction_id}")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=150,
        bbox_inches="tight",
    )
    plt.close()

    buf.seek(0)

    return {
        "transaction_id": transaction_id,
        "chart_base64": base64.b64encode(buf.read()).decode(),
        "format": "png",
    }