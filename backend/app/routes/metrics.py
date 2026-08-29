from fastapi import APIRouter
from pathlib import Path
import json

router = APIRouter()

METRICS_PATH = Path(__file__).parent.parent / "ml" / "artifacts" / "evaluation_metrics.json"


@router.get("/metrics/model-performance")
def get_model_performance():
    """Serve the full model evaluation report from held-out test set."""
    if not METRICS_PATH.exists():
        return {
            "status": "not_ready",
            "message": "Run ml/evaluation.py to generate evaluation_metrics.json",
        }

    with open(METRICS_PATH, "r") as f:
        report = json.load(f)

    return {
        "status": "ready",
        "evaluated_at": report.get("evaluated_at"),
        "test_set": report.get("test_set"),
        "models": report.get("models"),
        "limitations": report.get("limitations"),
        "honest_assessment": report.get("honest_assessment"),
    }