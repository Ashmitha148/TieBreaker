import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from ..database import get_db
from ..models import Decision
from ..services.strike_selector import (
    calculate_action_losses,
    threshold_baseline_decision,
)
from ..ml.models import get_model_manager

router = APIRouter()


def _enrich_decision(decision: Decision) -> dict:
    """Convert a DB Decision into a full stream payload using stored features."""
    record = None

    if decision.feature_snapshot:
        try:
            record = json.loads(decision.feature_snapshot)
        except Exception:
            record = None

    fraud_prob = decision.fraud_prob
    fp_prob = decision.fp_prob

    result = calculate_action_losses(
        fraud_prob,
        fp_prob,
        decision.amount,
        decision.ltv,
    )
    baseline = threshold_baseline_decision(fraud_prob)

    # Only calculate SHAP when the original feature snapshot exists.
    # Do not invent feature values for missing data.
    if record:
        mgr = get_model_manager()
        drivers = mgr.get_shap_drivers(record, top_n=3)
    else:
        drivers = []

    baseline_loss = result["losses"].get(
        baseline,
        result["losses"]["BLOCK"],
    )
    optimal_loss = result["losses"][result["recommended_action"]]
    savings = decision.savings_vs_baseline

    return {
        "transaction": {
            "transaction_id": decision.transaction_id,
            "amount": decision.amount,
            "ltv": decision.ltv,
            "merchant_category": decision.merchant_category,
            "fraud_probability": fraud_prob,
            "fp_probability": fp_prob,
            "timestamp": (
                decision.created_at.isoformat()
                if decision.created_at
                else datetime.now().isoformat()
            ),
        },
        "prediction": {
            "fraud_probability": fraud_prob,
            "fp_probability": fp_prob,
            "shap_drivers": drivers,
        },
        "decision": {
            "recommended_action": result["recommended_action"],
            "baseline_action": baseline,
            "losses": result["losses"],
            "primary_reason": result["primary_reason"],
            "is_counterintuitive": result["is_counterintuitive"],
            "confidence_gap": result["confidence_gap"],
        },
        "financial_impact": {
            "baseline_loss_inr": baseline_loss,
            "optimal_loss_inr": optimal_loss,
            "savings_inr": round(savings, 2),
            "ltv_at_risk": (
                decision.ltv
                if baseline == "BLOCK"
                and result["recommended_action"] != "BLOCK"
                else 0
            ),
        },
    }


async def _stream_from_db(db_factory, delay_ms: int) -> AsyncGenerator:
    """Yield SSE events by querying the database with fresh sessions."""
    total_savings = 0.0
    tx_count = 0

    while True:
        db = next(db_factory())

        try:
            decisions = (
                db.query(Decision)
                .order_by(Decision.created_at.desc())
                .limit(100)
                .all()
            )
        finally:
            db.close()

        if not decisions:
            yield {
                "event": "status",
                "data": json.dumps(
                    {
                        "type": "status",
                        "message": "No decisions in database. Seed with POST /api/demo/seed-decisions",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            }

            await asyncio.sleep(3)
            continue

        for decision in decisions:
            tx_count += 1

            data = _enrich_decision(decision)

            total_savings += data["financial_impact"]["savings_inr"]

            payload = {
                "type": "transaction",
                "sequence": tx_count,
                "data": data,
                "running_totals": {
                    "transactions_processed": tx_count,
                    "total_savings_inr": round(total_savings, 2),
                    "avg_savings_per_tx": (
                        round(total_savings / tx_count, 2)
                        if tx_count
                        else 0
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

            yield {
                "event": "transaction",
                "data": json.dumps(payload),
            }

            await asyncio.sleep(delay_ms / 1000)


@router.get("/stream/transactions")
def stream_transactions(delay_ms: int = 1500):
    """
    SSE endpoint streaming real persisted decisions from the database.
    """
    return EventSourceResponse(
        _stream_from_db(get_db, delay_ms)
    )


@router.get("/stream/snapshot")
def stream_snapshot():
    """Get a snapshot of the 10 most recent real decisions."""
    db = next(get_db())

    try:
        decisions = (
            db.query(Decision)
            .order_by(Decision.created_at.desc())
            .limit(10)
            .all()
        )

        txs = [_enrich_decision(d) for d in decisions]

        total_savings = sum(
            t["financial_impact"]["savings_inr"]
            for t in txs
        )

        return {
            "transactions": txs,
            "summary": {
                "count": len(txs),
                "total_savings_inr": round(total_savings, 2),
                "counterintuitive_count": sum(
                    1
                    for t in txs
                    if t["decision"]["is_counterintuitive"]
                ),
                "source": "database",
            },
        }
    finally:
        db.close()