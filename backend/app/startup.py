import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.train_models import (
    load_csv, train_fraud_model, train_fp_model, train_review_model, evaluate_model,
    ARTIFACTS_DIR, FRAUD_FEATURES, FP_FEATURES, REVIEW_FEATURES
)
import pickle


def ensure_models_trained():
    """Train models if artifacts don't exist. Call this on startup."""
    fraud_path = ARTIFACTS_DIR / "fraud_model.pkl"
    fp_path = ARTIFACTS_DIR / "fp_model.pkl"
    review_path = ARTIFACTS_DIR / "review_model.pkl"

    if fraud_path.exists() and fp_path.exists() and review_path.exists():
        print("INFO: ML model artifacts found. Skipping training.")
        return

    print("INFO: Training ML models...")
    DATA_DIR = Path(__file__).parent / "ml" / "data"

    try:
        train = load_csv(DATA_DIR / "train.csv")
        test = load_csv(DATA_DIR / "test.csv")
    except FileNotFoundError:
        print("WARNING: train.csv/test.csv not found. Models will use rule-based fallback.")
        return

    print("INFO: Training fraud model...")
    fraud_model = train_fraud_model(train)
    fraud_metrics = evaluate_model(fraud_model, test, FRAUD_FEATURES, "is_fraud")
    print("Fraud metrics:", fraud_metrics)

    print("INFO: Training FP model...")
    fp_model = train_fp_model(train)
    fp_metrics = evaluate_model(fp_model, test, FP_FEATURES, "is_false_positive")
    print("FP metrics:", fp_metrics)

    print("INFO: Training review time model...")
    review_model = train_review_model(train)
    review_metrics = evaluate_model(review_model, test, REVIEW_FEATURES, is_regression=True)
    print("Review metrics:", review_metrics)

    artifacts = {
        "fraud": {"model": fraud_model, "features": FRAUD_FEATURES, "metrics": fraud_metrics},
        "fp": {"model": fp_model, "features": FP_FEATURES, "metrics": fp_metrics},
        "review": {"model": review_model, "features": REVIEW_FEATURES, "metrics": review_metrics},
    }

    for name, data in artifacts.items():
        with open(ARTIFACTS_DIR / f"{name}_model.pkl", "wb") as f:
            pickle.dump(data, f)

    print(f"INFO: All models saved to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    ensure_models_trained()
