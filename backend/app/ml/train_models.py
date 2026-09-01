"""
TieBreaker model training pipeline — real IEEE-CIS data only.

Trains:
  1. Fraud detection model (GradientBoostingClassifier)
  2. False-positive model (GradientBoostingClassifier + SMOTE)

Validation-only threshold tuning is performed on the validation split.
Test-set metrics are reported but NEVER used to pick thresholds.

Artifacts are persisted as .joblib with SHA-256 sidecars.
"""
import hashlib
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
)

from .data import load_data, get_feature_matrix, FRAUD_FEATURES, FP_FEATURES

BASE_DIR = Path(__file__).parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

FRAUD_MODEL_PATH = ARTIFACTS_DIR / "fraud_model.joblib"
FP_MODEL_PATH = ARTIFACTS_DIR / "fp_model.joblib"
FRAUD_THRESHOLD_PATH = ARTIFACTS_DIR / "fraud_threshold.joblib"
FP_THRESHOLD_PATH = ARTIFACTS_DIR / "fp_threshold.joblib"


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _save_artifact(data, path: Path):
    """Persist artifact as .joblib with a SHA-256 sidecar file."""
    joblib.dump(data, path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(_compute_sha256(path))


def _train_fraud_model(X_train: np.ndarray, y_train: np.ndarray):
    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=4, random_state=42
    )
    model.fit(X_train, y_train)
    return model


def _train_fp_model(X_train: np.ndarray, y_train: np.ndarray):
    """Train FP model with SMOTE oversampling for the minority class."""
    try:
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(random_state=42)
        X_res, y_res = smote.fit_resample(X_train, y_train)
        model = GradientBoostingClassifier(
            n_estimators=80, max_depth=3, random_state=42
        )
        model.fit(X_res, y_res)
        return model
    except ImportError:
        warnings.warn(
            "imbalanced-learn not installed; training FP model without SMOTE"
        )
        model = GradientBoostingClassifier(
            n_estimators=80, max_depth=3, random_state=42
        )
        model.fit(X_train, y_train)
        return model


def _tune_threshold(
    model,
    X_val: np.ndarray,
    y_val: np.ndarray,
    target_metric: str = "recall",
    target_value: float = 0.45,
):
    proba = model.predict_proba(X_val)[:, 1]
    best_threshold = 0.5
    best_score = 0.0

    for threshold in np.arange(0.10, 0.90, 0.01):
        y_pred = (proba >= threshold).astype(int)
        if target_metric == "recall":
            score = recall_score(y_val, y_pred, zero_division=0)
        elif target_metric == "f1":
            score = f1_score(y_val, y_pred, zero_division=0)
        else:
            score = f1_score(y_val, y_pred, zero_division=0)

        if score >= target_value and score > best_score:
            best_score = score
            best_threshold = round(threshold, 2)

    return best_threshold, best_score


def evaluate(
    model, X: np.ndarray, y: np.ndarray, threshold: float = 0.5
) -> dict:
    proba = model.predict_proba(X)[:, 1]
    y_pred = (proba >= threshold).astype(int)

    return {
        "precision": round(precision_score(y, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y, y_pred, zero_division=0), 3),
        "f1": round(f1_score(y, y_pred, zero_division=0), 3),
        "pr_auc": round(average_precision_score(y, proba), 3),
        "roc_auc": round(roc_auc_score(y, proba), 3),
    }


def train_all():
    """Main training entry point."""
    print("Loading real IEEE-CIS data...")
    train, val, test = load_data()
    print(f"Loaded: train={len(train)}, val={len(val)}, test={len(test)}")

    X_train_fraud = get_feature_matrix(train, FRAUD_FEATURES)
    y_train_fraud = train["isFraud"].values
    X_val_fraud = get_feature_matrix(val, FRAUD_FEATURES)
    y_val_fraud = val["isFraud"].values
    X_test_fraud = get_feature_matrix(test, FRAUD_FEATURES)
    y_test_fraud = test["isFraud"].values

    print("Training fraud model...")
    fraud_model = _train_fraud_model(X_train_fraud, y_train_fraud)
    fraud_threshold, _ = _tune_threshold(
        fraud_model, X_val_fraud, y_val_fraud,
        target_metric="f1", target_value=0.50,
    )
    fraud_metrics = evaluate(
        fraud_model, X_test_fraud, y_test_fraud, threshold=fraud_threshold
    )
    print(f"Fraud metrics (threshold={fraud_threshold}):", fraud_metrics)

    X_train_fp = get_feature_matrix(train, FP_FEATURES)
    y_train_fp = train["is_false_positive"].values
    X_val_fp = get_feature_matrix(val, FP_FEATURES)
    y_val_fp = val["is_false_positive"].values
    X_test_fp = get_feature_matrix(test, FP_FEATURES)
    y_test_fp = test["is_false_positive"].values

    print("Training FP model with SMOTE...")
    fp_model = _train_fp_model(X_train_fp, y_train_fp)
    fp_threshold, fp_recall = _tune_threshold(
        fp_model, X_val_fp, y_val_fp,
        target_metric="recall", target_value=0.45,
    )
    fp_metrics = evaluate(
        fp_model, X_test_fp, y_test_fp, threshold=fp_threshold
    )
    print(f"FP metrics (threshold={fp_threshold}):", fp_metrics)

    if fp_metrics.get("recall", 0) < 0.45:
        warnings.warn(
            f"TEST FP recall {fp_metrics.get('recall', 0):.3f} < 0.45 target. "
            "Consider feature engineering, hyper-parameter tuning, or a "
            "different model architecture."
        )

    _save_artifact(
        {
            "model": fraud_model,
            "features": FRAUD_FEATURES,
            "metrics": fraud_metrics,
            "threshold": fraud_threshold,
            "version": "gbc-fraud-v2",
        },
        FRAUD_MODEL_PATH,
    )

    _save_artifact(
        {
            "model": fp_model,
            "features": FP_FEATURES,
            "metrics": fp_metrics,
            "threshold": fp_threshold,
            "version": "gbc-fp-v2",
        },
        FP_MODEL_PATH,
    )

    _save_artifact({"threshold": fraud_threshold}, FRAUD_THRESHOLD_PATH)
    _save_artifact({"threshold": fp_threshold}, FP_THRESHOLD_PATH)

    print(f"Artifacts saved to {ARTIFACTS_DIR}")
    print("  - fraud_model.joblib")
    print("  - fp_model.joblib")
    print("  - fraud_threshold.joblib")
    print("  - fp_threshold.joblib")


if __name__ == "__main__":
    train_all()