"""
TieBreaker model training pipeline — Phase 2: Optuna + Calibration + MLflow.

Trains:
  1. Fraud detection model (GradientBoostingClassifier, Optuna-tuned, calibrated)
  2. False-positive model (GradientBoostingClassifier + SMOTE, recall-optimised)

Artifacts are persisted as .joblib with SHA-256 sidecars.
"""
import hashlib
import logging
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .data import load_data, get_feature_matrix, FRAUD_FEATURES, FP_FEATURES

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

FRAUD_MODEL_PATH = ARTIFACTS_DIR / "fraud_model.joblib"
FP_MODEL_PATH = ARTIFACTS_DIR / "fp_model.joblib"
FRAUD_CALIBRATED_PATH = ARTIFACTS_DIR / "fraud_model_calibrated.joblib"
FRAUD_SHADOW_PATH = ARTIFACTS_DIR / "fraud_model_shadow.joblib"
FRAUD_THRESHOLD_PATH = ARTIFACTS_DIR / "fraud_threshold.joblib"
FP_THRESHOLD_PATH = ARTIFACTS_DIR / "fp_threshold.joblib"


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _save_artifact(data, path: Path):
    """Persist artifact as .joblib with a SHA-256 sidecar file."""
    joblib.dump(data, path)
    path.with_suffix(path.suffix + ".sha256").write_text(_compute_sha256(path))


def _optuna_objective(trial, X_train, y_train, X_val, y_val):
    """Optuna objective: maximise F1 on validation set."""
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 50, 200),
        "max_depth": trial.suggest_int("max_depth", 3, 6),
        "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.2),
    }
    model = GradientBoostingClassifier(**params, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_val)
    return f1_score(y_val, y_pred, zero_division=0)


def _run_optuna(X_train, y_train, X_val, y_val, n_trials: int = 20, study_name: str = "study"):
    """Run Optuna hyperparameter search, return best_params."""
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="maximize", study_name=study_name)
        study.optimize(
            lambda trial: _optuna_objective(trial, X_train, y_train, X_val, y_val),
            n_trials=n_trials,
        )
        logger.info("Best params (%s): %s | F1=%.4f", study_name, study.best_params, study.best_value)
        return study.best_params
    except Exception as e:
        warnings.warn(f"Optuna failed ({e}); using default params.")
        return {"n_estimators": 100, "max_depth": 4, "learning_rate": 0.1}


def _train_fp_model(X_train: np.ndarray, y_train: np.ndarray):
    """
    Train FP model with SMOTE (sampling_strategy=0.5) + balanced sample weights.
    Uses 150 estimators. Threshold is tuned on validation data to meet a
    recall floor while maximising F1 (precision-preserving).
    FP model is inherently harder on synthetic labels; we target recall >= 0.30
    while maintaining precision > 0.50.

    Note: GradientBoostingClassifier has no ``class_weight`` parameter — class
    balancing is applied via per-sample weights (n_samples / (n_classes *
    class_count)), the technically correct equivalent.
    """
    try:
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(sampling_strategy=0.5, random_state=42)
        X_res, y_res = smote.fit_resample(X_train, y_train)
    except ImportError:
        warnings.warn("imbalanced-learn not installed; training FP without SMOTE")
        X_res, y_res = X_train, y_train

    y_res = np.asarray(y_res)
    model = GradientBoostingClassifier(
        n_estimators=150, max_depth=3, random_state=42
    )
    classes, counts = np.unique(y_res, return_counts=True)
    sample_weight = np.empty(len(y_res), dtype=np.float64)
    for cls, cnt in zip(classes, counts):
        sample_weight[y_res == cls] = len(y_res) / (2.0 * cnt)
    model.fit(X_res, y_res, sample_weight=sample_weight)
    return model


def _tune_threshold(model, X_val, y_val, target_metric="recall", target_value=0.45):
    """
    Select the decision threshold on validation data (never on test data).

    Among thresholds that meet the target-metric floor (e.g. recall >= 0.30),
    pick the one with the best F1 — ties broken toward the higher threshold.
    This replaces the degenerate "first/most permissive threshold meeting the
    floor" behaviour, which inflated recall at the expense of precision.
    If no threshold reaches the floor, fall back to the best value of the
    target metric and warn.
    """
    proba = model.predict_proba(X_val)[:, 1]
    candidates = []
    for threshold in np.arange(0.10, 0.90, 0.01):
        y_pred = (proba >= threshold).astype(int)
        candidates.append({
            "threshold": round(float(threshold), 2),
            "recall": recall_score(y_val, y_pred, zero_division=0),
            "precision": precision_score(y_val, y_pred, zero_division=0),
            "f1": f1_score(y_val, y_pred, zero_division=0),
        })

    meeting = [c for c in candidates if c[target_metric] >= target_value]
    if meeting:
        best = max(meeting, key=lambda c: (c["f1"], c["threshold"]))
    else:
        best = max(candidates, key=lambda c: (c[target_metric], c["threshold"]))
        warnings.warn(
            f"No validation threshold reached {target_metric}={target_value}; "
            f"using best {target_metric}={best[target_metric]:.3f} "
            f"at threshold={best['threshold']}."
        )

    logger.info(
        "Threshold selected: %.2f (recall=%.3f precision=%.3f f1=%.3f)",
        best["threshold"], best["recall"], best["precision"], best["f1"],
    )
    return best["threshold"], best[target_metric]


def evaluate(model, X, y, threshold=0.5) -> dict:
    proba = model.predict_proba(X)[:, 1]
    y_pred = (proba >= threshold).astype(int)
    return {
        "precision": round(precision_score(y, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y, y_pred, zero_division=0), 3),
        "f1": round(f1_score(y, y_pred, zero_division=0), 3),
        "pr_auc": round(average_precision_score(y, proba), 3),
        "roc_auc": round(roc_auc_score(y, proba), 3),
        "brier": round(brier_score_loss(y, proba), 4),
    }


def _log_mlflow(run_name: str, params: dict, metrics: dict, model):
    """Log params, metrics, and model to MLflow (local file:// tracking)."""
    try:
        import os
        import mlflow
        import mlflow.sklearn
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI") or "file:./mlruns"
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("tiebreaker_fraud_v2")
        with mlflow.start_run(run_name=run_name):
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)
            mlflow.sklearn.log_model(model, run_name)
        logger.info("MLflow run logged: %s", run_name)
    except Exception as e:
        warnings.warn(f"MLflow logging skipped: {e}")


def train_all(max_rows: int | None = None, optuna_trials: int = 20):
    """
    Main training entry point: Optuna → calibration → MLflow → artifacts.

    ``max_rows`` optionally caps the number of IEEE-CIS rows read (temporal
    head of the dataset) for smoke/validation runs — default None reads all.
    """
    print("Loading real IEEE-CIS data...")
    train, val, test = load_data(max_rows=max_rows)
    print(f"Loaded: train={len(train)}, val={len(val)}, test={len(test)}")

    # ── Fraud model ──────────────────────────────────────────────────────────
    X_tr_f = get_feature_matrix(train, FRAUD_FEATURES)
    y_tr_f = train["isFraud"].values
    X_va_f = get_feature_matrix(val, FRAUD_FEATURES)
    y_va_f = val["isFraud"].values
    X_te_f = get_feature_matrix(test, FRAUD_FEATURES)
    y_te_f = test["isFraud"].values

    print("Running Optuna for fraud model (%d trials)..." % optuna_trials)
    best_params_f = _run_optuna(X_tr_f, y_tr_f, X_va_f, y_va_f, n_trials=optuna_trials, study_name="fraud")

    print("Calibrating fraud model (isotonic, cv=5)...")
    # Re-train on train split only for calibration
    base_fraud = GradientBoostingClassifier(**best_params_f, random_state=42)
    calibrated_fraud = CalibratedClassifierCV(estimator=base_fraud, method="isotonic", cv=5)
    calibrated_fraud.fit(X_tr_f, y_tr_f)

    fraud_threshold, _ = _tune_threshold(calibrated_fraud, X_va_f, y_va_f, target_metric="f1", target_value=0.50)
    fraud_metrics = evaluate(calibrated_fraud, X_te_f, y_te_f, threshold=fraud_threshold)
    print(f"Fraud metrics (threshold={fraud_threshold}):", fraud_metrics)

    _log_mlflow("fraud_model", best_params_f, {k: v for k, v in fraud_metrics.items()}, calibrated_fraud)

    # ── FP model ─────────────────────────────────────────────────────────────
    X_tr_fp = get_feature_matrix(train, FP_FEATURES)
    y_tr_fp = train["is_false_positive"].values
    X_va_fp = get_feature_matrix(val, FP_FEATURES)
    y_va_fp = val["is_false_positive"].values
    X_te_fp = get_feature_matrix(test, FP_FEATURES)
    y_te_fp = test["is_false_positive"].values

    print("Training FP model with SMOTE (recall target=0.30)...")
    fp_model = _train_fp_model(X_tr_fp, y_tr_fp)
    # FP model: target recall=0.30 (inherently harder on synthetic labels)
    fp_threshold, _ = _tune_threshold(fp_model, X_va_fp, y_va_fp, target_metric="recall", target_value=0.30)
    fp_metrics = evaluate(fp_model, X_te_fp, y_te_fp, threshold=fp_threshold)
    print(f"FP metrics (threshold={fp_threshold}):", fp_metrics)

    if fp_metrics.get("recall", 0) < 0.25:
        warnings.warn(
            f"FP recall {fp_metrics['recall']:.3f} below 0.25 target. "
            "Investigate class balance or feature quality."
        )

    _log_mlflow("fp_model", {"n_estimators": 150, "max_depth": 3, "smote_strategy": 0.5},
                {k: v for k, v in fp_metrics.items()}, fp_model)

    # ── Save artifacts ────────────────────────────────────────────────────────
    _save_artifact(
        {"model": calibrated_fraud, "features": FRAUD_FEATURES, "metrics": fraud_metrics,
         "threshold": fraud_threshold, "version": "gbc-fraud-v2-calibrated", "best_params": best_params_f},
        FRAUD_MODEL_PATH,
    )
    _save_artifact(
        {"model": calibrated_fraud, "features": FRAUD_FEATURES, "metrics": fraud_metrics,
         "threshold": fraud_threshold, "version": "gbc-fraud-v2-calibrated", "best_params": best_params_f},
        FRAUD_CALIBRATED_PATH,
    )
    # Shadow model = same calibrated model (can swap to a newer architecture later)
    _save_artifact(
        {"model": calibrated_fraud, "features": FRAUD_FEATURES, "version": "shadow-v1"},
        FRAUD_SHADOW_PATH,
    )
    _save_artifact(
        {"model": fp_model, "features": FP_FEATURES, "metrics": fp_metrics,
         "threshold": fp_threshold, "version": "gbc-fp-v2"},
        FP_MODEL_PATH,
    )
    _save_artifact({"threshold": fraud_threshold}, FRAUD_THRESHOLD_PATH)
    _save_artifact({"threshold": fp_threshold}, FP_THRESHOLD_PATH)

    print(f"\nArtifacts saved to {ARTIFACTS_DIR}")
    for name in ["fraud_model.joblib", "fraud_model_calibrated.joblib",
                 "fraud_model_shadow.joblib", "fp_model.joblib",
                 "fraud_threshold.joblib", "fp_threshold.joblib"]:
        print(f"  ✓ {name}")
    return fraud_metrics, fp_metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_all()