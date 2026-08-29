"""
TieBreaker What-If Simulator
Lets users tweak transaction parameters and see how the decision changes.
Useful for: judge demos, analyst training, merchant onboarding.
"""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from ..services.strike_selector import calculate_action_losses, threshold_baseline_decision
from ..ml.predictor import predict_transaction
from ..auth import verify_api_key

router = APIRouter()
logger = logging.getLogger("tiebreaker.whatif")


class WhatIfRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Transaction amount in INR")
    ltv: float = Field(..., ge=0, description="Customer lifetime value in INR")
    velocity_1h: int = Field(0, ge=0, description="Transactions in last 1 hour")
    velocity_24h: int = Field(0, ge=0, description="Transactions in last 24 hours")
    device_change_flag: int = Field(0, ge=0, le=1)
    geo_mismatch_flag: int = Field(0, ge=0, le=1)
    is_cross_border: int = Field(0, ge=0, le=1)
    hour_of_day: int = Field(12, ge=0, le=23)
    customer_tenure_days: int = Field(365, ge=0)
    customer_tx_count_30d: int = Field(10, ge=0)
    customer_refund_rate: float = Field(0.0, ge=0, le=1)
    merchant_category: str = "Retail"
    payment_method: str = "upi"

    # Optional overrides to bypass model inference — now applied independently
    override_fraud_prob: Optional[float] = Field(None, ge=0, le=1)
    override_fp_prob: Optional[float] = Field(None, ge=0, le=1)


@router.post("/what-if")
def what_if_simulator(payload: WhatIfRequest, _api_key: str = Depends(verify_api_key)):
    """
    Simulate a TieBreaker decision with custom parameters.
    Returns: recommended action, baseline action, losses for all 4 actions, and savings.
    """
    # FIXED: unique, sign-safe ID instead of str(hash(...)) which could
    # produce a malformed "SIM--1234567" and used the deprecated .dict().
    sim_id = "SIM-" + uuid.uuid4().hex[:8].upper()

    record = {
        "transaction_id": sim_id,
        "amount": payload.amount,
        "ltv": payload.ltv,
        "velocity_1h": payload.velocity_1h,
        "velocity_24h": payload.velocity_24h,
        "device_change_flag": payload.device_change_flag,
        "geo_mismatch_flag": payload.geo_mismatch_flag,
        "is_cross_border": payload.is_cross_border,
        "hour_of_day": payload.hour_of_day,
        "customer_tenure_days": payload.customer_tenure_days,
        "customer_tx_count_30d": payload.customer_tx_count_30d,
        "customer_refund_rate": payload.customer_refund_rate,
        "merchant_category": payload.merchant_category,
        "payment_method": payload.payment_method,
    }

    # FIXED: each override now applies independently. Previously BOTH had to
    # be set or the whole override was silently ignored — a single override
    # from a demo user would silently fall through to live model inference
    # with no warning.
    shap_drivers = []
    used_model = False
    prediction = None

    needs_model = payload.override_fraud_prob is None or payload.override_fp_prob is None
    if needs_model:
        try:
            prediction = predict_transaction(record)
        except Exception:
            logger.exception("Model inference failed for what-if simulation %s", sim_id)
            raise HTTPException(status_code=500, detail="Model inference failed. See server logs.")
        used_model = True
        shap_drivers = prediction["shap_drivers"]

    if payload.override_fraud_prob is not None:
        fraud_prob = payload.override_fraud_prob
    else:
        fraud_prob = prediction["fraud_probability"]

    if payload.override_fp_prob is not None:
        fp_prob = payload.override_fp_prob
    else:
        fp_prob = prediction["fp_probability"]

    # If only one side was overridden, the shap_drivers reflect the model
    # call but only partially explain the blended result — flag that clearly
    # rather than silently presenting a "clean" model explanation.
    partial_override = (payload.override_fraud_prob is not None) != (payload.override_fp_prob is not None)

    result = calculate_action_losses(fraud_prob, fp_prob, payload.amount, payload.ltv)
    baseline = threshold_baseline_decision(fraud_prob)

    baseline_loss = result["losses"].get(baseline, result["losses"]["BLOCK"])
    optimal_loss = result["losses"][result["recommended_action"]]
    savings = max(0, baseline_loss - optimal_loss)

    return {
        "simulated_transaction": {
            "amount": payload.amount,
            "ltv": payload.ltv,
            "merchant_category": payload.merchant_category,
        },
        "model_inference": {
            "fraud_probability": fraud_prob,
            "fp_probability": fp_prob,
            "shap_drivers": shap_drivers,
            "used_live_model": used_model,
            "partial_override_note": (
                "One probability was overridden and the other came from the live model — "
                "SHAP drivers only explain the live-model side."
                if partial_override else None
            ),
        },
        "decision": {
            "recommended_action": result["recommended_action"],
            "baseline_action": baseline,
            "primary_reason": result["primary_reason"],
            "is_counterintuitive": result["is_counterintuitive"],
            "confidence_gap": result["confidence_gap"],
        },
        "financial_analysis": {
            "losses_by_action": result["losses"],
            "baseline_loss_inr": baseline_loss,
            "optimal_loss_inr": optimal_loss,
            "savings_vs_baseline_inr": round(savings, 2),
            "ltv_at_risk": payload.ltv if baseline == "BLOCK" and result["recommended_action"] != "BLOCK" else 0,
        },
        # FIXED: sensitivity analysis now uses the SAME fraud_prob/fp_prob as
        # the actual decision above, instead of hardcoded 0.5/0.2 defaults
        # that made this panel describe a different, generic transaction.
        "parameter_sensitivity": _compute_sensitivity(payload, fraud_prob, fp_prob),
    }


def _compute_sensitivity(payload: WhatIfRequest, fraud_prob: float, fp_prob: float) -> dict:
    """Show how the decision changes if key parameters shift ±20%.
    FIXED: now takes the transaction's actual fraud/fp probabilities instead
    of silently defaulting to 0.5/0.2 regardless of what was really predicted."""
    base_result = calculate_action_losses(fraud_prob, fp_prob, payload.amount, payload.ltv)
    base_action = base_result["recommended_action"]

    sensitivities = {}

    ltv_up = calculate_action_losses(fraud_prob, fp_prob, payload.amount, payload.ltv * 1.2)
    sensitivities["ltv_plus_20pct"] = {
        "ltv": round(payload.ltv * 1.2, 2),
        "recommended_action": ltv_up["recommended_action"],
        "changes": ltv_up["recommended_action"] != base_action,
    }

    ltv_down = calculate_action_losses(fraud_prob, fp_prob, payload.amount, payload.ltv * 0.8)
    sensitivities["ltv_minus_20pct"] = {
        "ltv": round(payload.ltv * 0.8, 2),
        "recommended_action": ltv_down["recommended_action"],
        "changes": ltv_down["recommended_action"] != base_action,
    }

    amt_up = calculate_action_losses(fraud_prob, fp_prob, payload.amount * 1.2, payload.ltv)
    sensitivities["amount_plus_20pct"] = {
        "amount": round(payload.amount * 1.2, 2),
        "recommended_action": amt_up["recommended_action"],
        "changes": amt_up["recommended_action"] != base_action,
    }

    return sensitivities