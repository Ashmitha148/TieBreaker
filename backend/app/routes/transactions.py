from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import json
import logging
import numpy as np

from ..database import get_db
from ..models import Decision, Override, AuditLog
from ..services.strike_selector import calculate_action_losses, threshold_baseline_decision
from ..ml.predictor import predict_transaction
from ..ml.models import get_model_manager
from ..services.velocity_engine import get_velocity_engine
from ..config import settings
from ..auth import verify_api_key
from ..rate_limit import limiter

router = APIRouter()
logger = logging.getLogger("tiebreaker.transactions")


class TransactionRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1)
    customer_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    ltv: float = Field(..., ge=0)
    merchant_category: str = "Retail"
    device_change_flag: int = 0
    geo_mismatch_flag: int = 0
    is_cross_border: int = 0
    hour_of_day: int = Field(12, ge=0, le=23)
    customer_tenure_days: int = Field(365, ge=0)
    customer_tx_count_30d: int = Field(10, ge=0)
    customer_refund_rate: float = Field(0.0, ge=0, le=1)
    payment_method: str = "upi"
    device_id: Optional[str] = None


def _get_velocity_engine():
    return get_velocity_engine(
        redis_url=settings.REDIS_URL or "redis://localhost:6379/0",
        fail_silent=True,
    )


def _redis_error_types():
    types = [OSError, RuntimeError, ConnectionError, TimeoutError]
    try:
        from redis.exceptions import RedisError
        types.append(RedisError)
    except ImportError:
        pass
    return tuple(types)


def _get_velocity_from_redis(engine, customer_id: str, device_id: str = None) -> dict:
    zeros = {"velocity_1h": 0, "velocity_24h": 0, "device_tx_count_1h": 0, "source": "fallback_zero"}
    try:
        velocity = engine.get_velocity(customer_id, device_id)
        if velocity.get("degraded"):
            velocity["source"] = "fallback_zero"
        else:
            velocity["source"] = "redis"
        return velocity
    except _redis_error_types() as exc:
        logger.warning(
            "Redis velocity lookup failed for customer_id=%s (%s: %s)",
            customer_id,
            type(exc).__name__,
            exc,
        )
        return zeros


@router.post("/transactions")
@limiter.limit("100/minute")
def create_transaction(
    request: Request,
    payload: TransactionRequest,
    db: Session = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    existing = db.query(Decision).filter(Decision.transaction_id == payload.transaction_id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Transaction {payload.transaction_id} was already scored (decision_id={existing.id}).",
        )

    engine = _get_velocity_engine()
    velocity = _get_velocity_from_redis(engine, payload.customer_id, payload.device_id)

    record = {
        "transaction_id": payload.transaction_id,
        "amount": payload.amount,
        "ltv": payload.ltv,
        "velocity_1h": velocity.get("velocity_1h", 0),
        "velocity_24h": velocity.get("velocity_24h", 0),
        "device_change_flag": payload.device_change_flag,
        "geo_mismatch_flag": payload.geo_mismatch_flag,
        "is_cross_border": payload.is_cross_border,
        "hour_of_day": payload.hour_of_day,
        "customer_tenure_days": payload.customer_tenure_days,
        "customer_tx_count_30d": payload.customer_tx_count_30d,
        "customer_refund_rate": payload.customer_refund_rate,
        "merchant_category": payload.merchant_category,
        "payment_method": payload.payment_method,
        "customer_id": payload.customer_id,
        "device_id": payload.device_id,
    }

    prediction = predict_transaction(record)
    fraud_prob = prediction["fraud_probability"]
    fp_prob = prediction["fp_probability"]
    record["fraud_prob"] = fraud_prob
    record["fp_prob"] = fp_prob

    result = calculate_action_losses(fraud_prob, fp_prob, payload.amount, payload.ltv)
    baseline = threshold_baseline_decision(fraud_prob)

    savings = round(
        result["losses"].get(baseline, result["losses"]["BLOCK"]) - result["losses"][result["recommended_action"]],
        2,
    )

    try:
        model_meta = get_model_manager().current_version_info()
    except AttributeError:
        logger.warning("Model manager has no current_version_info(); using unloaded")
        model_meta = {"version": "unloaded"}

    decision = Decision(
        transaction_id=payload.transaction_id,
        fraud_prob=fraud_prob,
        fp_prob=fp_prob,
        amount=payload.amount,
        ltv=payload.ltv,
        merchant_category=payload.merchant_category,
        recommended_action=result["recommended_action"],
        baseline_action=baseline,
        savings_vs_baseline=savings,
        model_version=model_meta.get("version", "unknown"),
        config_version="1.0",
        is_counterintuitive=result["is_counterintuitive"],
        feature_snapshot=json.dumps(record),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    db.add(AuditLog(
        user="system",
        action="DECISION_CREATED",
        entity_type="Decision",
        entity_id=payload.transaction_id,
        details=json.dumps({
            "recommended_action": result["recommended_action"],
            "velocity_source": velocity.get("source"),
            "model_version": model_meta.get("version", "unknown"),
        }),
        model_version=model_meta.get("version", "unknown"),
    ))
    db.commit()

    try:
        engine.record_transaction(payload.customer_id, payload.amount, payload.device_id)
    except _redis_error_types() as exc:
        logger.warning(
            "Failed to record transaction into Redis for customer_id=%s (%s: %s)",
            payload.customer_id,
            type(exc).__name__,
            exc,
        )

    return {
        "transaction_id": payload.transaction_id,
        "recommended_action": result["recommended_action"],
        "baseline_action": baseline,
        "fraud_probability": fraud_prob,
        "fp_probability": fp_prob,
        "savings_vs_baseline": savings,
        "is_counterintuitive": result["is_counterintuitive"],
        "velocity": velocity,
        "velocity_source": velocity.get("source", "fallback_zero"),
        "model_version": model_meta.get("version", "unloaded"),
    }


@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    decision = db.query(Decision).filter(Decision.transaction_id == transaction_id).first()

    if not decision:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found. Use POST /api/transactions to ingest real data, "
                   f"or POST /api/demo/seed-decisions to generate demo transactions.",
        )

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
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found.")

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
    import io
    import base64
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap

    decision = db.query(Decision).filter(Decision.transaction_id == transaction_id).first()
    if not decision or not decision.feature_snapshot:
        raise HTTPException(status_code=404, detail="Transaction or feature snapshot not found")

    record = json.loads(decision.feature_snapshot)
    mgr = get_model_manager()

    features = []
    for f in mgr.fraud_features:
        if f == "merchant_category_encoded":
            features.append(
                {"Retail": 0, "SaaS": 1, "B2B": 2, "Food": 3}.get(record.get("merchant_category", "Retail"), 0)
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
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close()
    buf.seek(0)

    return {
        "transaction_id": transaction_id,
        "chart_base64": base64.b64encode(buf.read()).decode(),
        "format": "png",
    }