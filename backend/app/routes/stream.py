import json
import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from ..database import get_db
from ..models import Decision
from ..auth import verify_api_key
from ..ml.predictor import predict_transaction
from ..ml.models import get_model_manager

router = APIRouter()


def _stream_from_db(db_gen, delay_ms: int):
    """Generator that yields SSE events from the database."""
    db = next(db_gen)
    try:
        seq = 0
        while True:
            now = datetime.now()
            decisions = (
                db.query(Decision)
                .order_by(Decision.created_at.desc())
                .limit(10)
                .all()
            )

            for d in decisions:
                record = {
                    "TransactionAmt": d.amount,
                    "amount": d.amount,
                    "hour_of_day": now.hour,
                    "day_of_week": now.weekday(),
                    "device_change_flag": 0,
                    "geo_mismatch_flag": 0,
                    "is_cross_border": 0,
                    "customer_tenure_days": 365,
                    "customer_tx_count_30d": 10,
                    "customer_refund_rate": 0.0,
                    "velocity_1h": 0,
                    "velocity_24h": 0,
                }

                prediction = predict_transaction(record)
                mgr = get_model_manager()
                drivers = mgr.get_shap_drivers(record, top_n=3)

                payload = {
                    "type": "transaction",
                    "sequence": seq,
                    "data": {
                        "transaction": {
                            "transaction_id": d.transaction_id,
                            "amount": d.amount,
                            "ltv": d.ltv,
                            "merchant_category": d.merchant_category or "Retail",
                            "fraud_probability": d.fraud_prob,
                            "fp_probability": d.fp_prob,
                            "timestamp": d.created_at.isoformat() if d.created_at else now.isoformat(),
                        },
                        "prediction": {
                            "fraud_probability": prediction["fraud_probability"],
                            "fp_probability": prediction["fp_probability"],
                            "shap_drivers": drivers,
                        },
                        "decision": {
                            "recommended_action": d.recommended_action,
                            "baseline_action": d.baseline_action,
                            "losses": prediction.get("losses", {}),
                            "primary_reason": prediction.get("primary_reason", ""),
                            "is_counterintuitive": d.is_counterintuitive,
                            "confidence_gap": prediction.get("confidence_gap", 0),
                        },
                        "financial_impact": {
                            "baseline_loss_inr": prediction.get("baseline_loss_inr", 0),
                            "optimal_loss_inr": prediction.get("optimal_loss_inr", 0),
                            "savings_inr": prediction.get("savings_inr", 0),
                            "ltv_at_risk": prediction.get("ltv_at_risk", 0),
                        },
                    },
                    "running_totals": {
                        "transactions_processed": seq + 1,
                        "total_savings_inr": prediction.get("savings_inr", 0) * (seq + 1),
                        "avg_savings_per_tx": prediction.get("savings_inr", 0),
                    },
                    "timestamp": now.isoformat(),
                }

                yield f"data: {json.dumps(payload)}"
                seq += 1
                asyncio.run(asyncio.sleep(delay_ms / 1000.0))
    finally:
        db_gen.close()


@router.get("/stream/transactions")
def stream_transactions(
    delay_ms: int = Query(1800, ge=100, le=10000),
    _api_key: str = Depends(verify_api_key),
):
    """SSE endpoint that streams synthetic transaction decisions in real-time."""
    db_gen = get_db()
    return EventSourceResponse(_stream_from_db(db_gen, delay_ms))