"""
TieBreaker ML Predictor — Clean inference API for production.
All model loading lives in models.py; this module provides the interface
that routes and services actually call.
"""

from typing import List, Dict, Any
from ..ml.models import get_model_manager, ModelManager


def predict_transaction(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run full dual-model inference on a single transaction record.
    Returns fraud prob, FP prob, review time estimate, and SHAP drivers.
    """
    mgr = get_model_manager()

    fraud_prob = mgr.predict_fraud_prob(record)
    fp_prob = mgr.predict_fp_prob(record)
    review_time = mgr.predict_review_time(record)
    drivers = mgr.get_shap_drivers(record, top_n=3)

    return {
        "fraud_probability": fraud_prob,
        "fp_probability": fp_prob,
        "review_time_minutes": review_time,
        "shap_drivers": drivers,
        "model_version": "2.0.0",
    }


def predict_batch(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch inference for queue processing or shadow mode."""
    return [predict_transaction(r) for r in records]


def get_model_health() -> Dict[str, Any]:
    """Health check for ML subsystem."""
    mgr = get_model_manager()
    return {
        "fraud_model_loaded": mgr.fraud_model is not None,
        "fp_model_loaded": mgr.fp_model is not None,
        "review_model_loaded": mgr.review_model is not None,
        "fraud_metrics": mgr.fraud_metrics,
        "fp_metrics": mgr.fp_metrics,
    }
    