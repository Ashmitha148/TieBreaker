import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.train_models import train_all, ARTIFACTS_DIR

def ensure_models_trained():
    fraud_path = ARTIFACTS_DIR / "fraud_model.joblib"
    fp_path = ARTIFACTS_DIR / "fp_model.joblib"

    if fraud_path.exists() and fp_path.exists():
        print("INFO: ML model artifacts found. Skipping training.")
        return

    print("INFO: Attempting to train ML models from real IEEE-CIS data...")
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