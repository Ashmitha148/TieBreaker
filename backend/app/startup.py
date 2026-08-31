import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.train_models import (
    load_data, train_all, ARTIFACTS_DIR, FRAUD_FEATURES, FP_FEATURES
)


def ensure_models_trained():
    """Train models if artifacts don't exist. Call this on startup."""
    fraud_path = ARTIFACTS_DIR / "fraud_model.joblib"
    fp_path = ARTIFACTS_DIR / "fp_model.joblib"

    if fraud_path.exists() and fp_path.exists():
        print("INFO: ML model artifacts found. Skipping training.")
        return

    print("INFO: Training ML models from real IEEE-CIS data...")

    try:
        train_all()
    except FileNotFoundError as e:
        print(f"WARNING: {e}")
        print("Models will use heuristic fallback until real data is provided.")
    except Exception as e:
        print(f"ERROR: Model training failed: {e}")
        print("Models will use heuristic fallback.")


if __name__ == "__main__":
    ensure_models_trained()
