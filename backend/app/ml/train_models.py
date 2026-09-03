"""TieBreaker model training — V2 (XGBoost, recall-optimized, calibrated).

CRITICAL FIXES from V1:
1. XGBClassifier instead of GradientBoostingClassifier (handles missing values, imbalanced data).
2. scale_pos_weight auto-computed from fraud rate (~28 for 3.5% fraud).
3. Optuna search space expanded (subsample, colsample_bytree, reg params).
4. Threshold tuned for BALANCED precision/recall (F1-optimizing), not just F1 floor.
5. Calibration uses TimeSeriesSplit (temporal folds) instead of random KFold.
6. FP model uses XGBoost + SMOTE with its own scale_pos_weight.
7. All artifacts saved as .joblib with SHA-256 sidecars (backward compatible).

Artifacts are persisted as .joblib with SHA-256 sidecars.
"""
import hashlib
import logging
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit

try:
    from .data import load_data, get_feature_matrix, FRAUD_FEATURES, FP_FEATURES
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from data import load_data, get_feature_matrix, FRAUD_FEATURES, FP_FEATURES

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


def _optuna_objective_xgb(trial, X_train, y_train, X_val, y_val, scale_pos_weight):
    """Optuna objective for XGBClassifier — maximize F1 on validation set."""
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "max_depth": trial.suggest_int("max_depth", 4, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.2, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0, 5),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        "scale_pos_weight": scale_pos_weight,
        "use_label_encoder": False,
        "eval_metric": "logloss",
        "random_state": 42,
        "n_jobs": -1,
    }
    try:
        from xgboost import XGBClassifier
    except ImportError:
        raise ImportError("xgboost is required. Install: pip install xgboost")

    model = XGBClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    y_pred = model.predict(X_val)
    return f1_score(y_val, y_pred, zero_division=0)


def _run_optuna_xgb(X_train, y_train, X_val, y_val, scale_pos_weight, n_trials=30, study_name="fraud"):
    """Run Optuna hyperparameter search, return best_params."""
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="maximize", study_name=study_name)
        study.optimize(
            lambda trial: _optuna_objective_xgb(trial, X_train, y_train, X_val, y_val, scale_pos_weight),
            n_trials=n_trials,
            show_progress_bar=True,
        )
        logger.info("Best params (%s): %s | F1=%.4f", study_name, study.best_params, study.best_value)
        return study.best_params
    except Exception as e:
        warnings.warn(f"Optuna failed ({e}); using default XGB params.")
        return {
            "n_estimators": 200, "max_depth": 6, "learning_rate": 0.1,
            "subsample": 0.9, "colsample_bytree": 0.9,
            "min_child_weight": 3, "gamma": 0, "reg_alpha": 0.1, "reg_lambda": 1.0,
        }


def _train_fp_model(X_train, y_train):
    """Train FP model with SMOTE + XGBoost."""
    try:
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(sampling_strategy=0.5, random_state=42)
        X_res, y_res = smote.fit_resample(X_train, y_train)
    except ImportError:
        warnings.warn("imbalanced-learn not installed; training FP without SMOTE")
        X_res, y_res = X_train, y_train

    y_res = np.asarray(y_res)
    try:
        from xgboost import XGBClassifier
    except ImportError:
        raise ImportError("xgboost is required.")

    classes, counts = np.unique(y_res, return_counts=True)
    scale_pos = counts[0] / counts[1] if len(counts) > 1 else 1.0

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        scale_pos_weight=scale_pos,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_res, y_res)
    return model


def _tune_threshold_balanced(model, X_val, y_val, target_precision=0.75, target_recall=0.65):
    """Tune threshold for balanced precision/recall.

    Strategy:
    1. Try to find thresholds where BOTH precision >= target_precision AND recall >= target_recall.
       Pick the one with best F1.
    2. If no threshold meets both, find the threshold closest to the intersection of
       precision=target_precision and recall=target_recall in PR space.
    3. Fall back to best F1.

    This produces a balanced operating point suitable for hackathon presentation.
    """
    proba = model.predict_proba(X_val)[:, 1]
    candidates = []
    for threshold in np.arange(0.05, 0.95, 0.005):
        y_pred = (proba >= threshold).astype(int)
        candidates.append({
            "threshold": round(float(threshold), 3),
            "recall": recall_score(y_val, y_pred, zero_division=0),
            "precision": precision_score(y_val, y_pred, zero_division=0),
            "f1": f1_score(y_val, y_pred, zero_division=0),
        })

    # Phase 1: Both targets met
    meeting_both = [c for c in candidates 
                    if c["recall"] >= target_recall and c["precision"] >= target_precision]
    if meeting_both:
        best = max(meeting_both, key=lambda c: (c["f1"], c["precision"]))
        logger.info("Balanced threshold (both targets met): %.3f (P=%.3f R=%.3f F1=%.3f)",
                    best["threshold"], best["precision"], best["recall"], best["f1"])
        return best["threshold"], best

    # Phase 2: Closest to balanced point in PR space
    # Minimize distance from (target_precision, target_recall)
    def _pr_distance(c):
        return ((c["precision"] - target_precision) ** 2 + 
                (c["recall"] - target_recall) ** 2) ** 0.5

    best_balanced = min(candidates, key=_pr_distance)

    # Only use balanced if it's reasonably close; otherwise fall back to best F1
    if _pr_distance(best_balanced) < 0.15:
        logger.info("Balanced threshold (closest to target): %.3f (P=%.3f R=%.3f F1=%.3f)",
                    best_balanced["threshold"], best_balanced["precision"], 
                    best_balanced["recall"], best_balanced["f1"])
        return best_balanced["threshold"], best_balanced

    # Phase 3: Best F1
    best_f1 = max(candidates, key=lambda c: c["f1"])
    warnings.warn(
        f"No threshold near balanced point. Using best F1={best_f1['f1']:.3f} "
        f"at threshold={best_f1['threshold']}."
    )
    return best_f1["threshold"], best_f1


def evaluate(model, X, y, threshold=0.5) -> dict:
    proba = model.predict_proba(X)[:, 1]
    y_pred = (proba >= threshold).astype(int)
    return {
        "precision": round(precision_score(y, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y, y_pred, zero_division=0), 4),
        "pr_auc": round(average_precision_score(y, proba), 4),
        "roc_auc": round(roc_auc_score(y, proba), 4),
        "brier": round(brier_score_loss(y, proba), 4),
    }


def _log_mlflow(run_name, params, metrics, model):
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


def train_all(max_rows: int | None = None, optuna_trials: int = 30):
    """Main training entry point: Optuna -> calibration -> threshold tuning -> artifacts.

    ``max_rows`` optionally caps the number of IEEE-CIS rows read.
    """
    print("Loading real IEEE-CIS data...")
    train, val, test = load_data(max_rows=max_rows)
    print(f"Loaded: train={len(train)}, val={len(val)}, test={len(test)}")

    fraud_rate = train["isFraud"].mean()
    fp_rate = train["is_false_positive"].mean()
    print(f"Train fraud rate: {fraud_rate:.4f} | FP rate: {fp_rate:.4f}")

    # ── Fraud model ──────────────────────────────────────────────────────
    X_tr_f = get_feature_matrix(train, FRAUD_FEATURES)
    y_tr_f = train["isFraud"].values
    X_va_f = get_feature_matrix(val, FRAUD_FEATURES)
    y_va_f = val["isFraud"].values
    X_te_f = get_feature_matrix(test, FRAUD_FEATURES)
    y_te_f = test["isFraud"].values

    scale_pos_weight = (1 - fraud_rate) / fraud_rate if fraud_rate > 0 else 1.0
    print(f"Fraud scale_pos_weight: {scale_pos_weight:.2f}")

    print(f"Running Optuna for fraud model ({optuna_trials} trials)...")
    best_params_f = _run_optuna_xgb(
        X_tr_f, y_tr_f, X_va_f, y_va_f,
        scale_pos_weight=scale_pos_weight,
        n_trials=optuna_trials,
        study_name="fraud_xgb"
    )

    print("Training final fraud model with best params...")
    try:
        from xgboost import XGBClassifier
    except ImportError:
        raise ImportError("xgboost is required. Install: pip install xgboost")

    final_params_f = {
        **best_params_f,
        "scale_pos_weight": scale_pos_weight,
        "use_label_encoder": False,
        "eval_metric": "logloss",
        "random_state": 42,
        "n_jobs": -1,
    }
    base_fraud = XGBClassifier(**final_params_f)
    base_fraud.fit(X_tr_f, y_tr_f, eval_set=[(X_va_f, y_va_f)], verbose=False)

    print("Calibrating fraud model (isotonic, temporal cv=5)...")
    # FIX: Use TimeSeriesSplit for calibration to prevent temporal leakage
    tscv = TimeSeriesSplit(n_splits=5)
    calibrated_fraud = CalibratedClassifierCV(
        estimator=base_fraud, method="isotonic", cv=tscv
    )
    calibrated_fraud.fit(X_tr_f, y_tr_f)

    print("Tuning threshold for balanced precision/recall (P>=0.75, R>=0.65)...")
    fraud_threshold, fraud_threshold_stats = _tune_threshold_balanced(
        calibrated_fraud, X_va_f, y_va_f, 
        target_precision=0.75, target_recall=0.65
    )

    fraud_metrics = evaluate(calibrated_fraud, X_te_f, y_te_f, threshold=fraud_threshold)
    print(f"Fraud metrics (threshold={fraud_threshold}):", fraud_metrics)

    _log_mlflow("fraud_model_xgb", best_params_f, 
                {k: v for k, v in fraud_metrics.items()}, calibrated_fraud)

    # ── FP model ─────────────────────────────────────────────────────────
    X_tr_fp = get_feature_matrix(train, FP_FEATURES)
    y_tr_fp = train["is_false_positive"].values
    X_va_fp = get_feature_matrix(val, FP_FEATURES)
    y_va_fp = val["is_false_positive"].values
    X_te_fp = get_feature_matrix(test, FP_FEATURES)
    y_te_fp = test["is_false_positive"].values

    print("Training FP model with SMOTE + XGBoost...")
    fp_model = _train_fp_model(X_tr_fp, y_tr_fp)

    print("Tuning FP threshold for balanced precision/recall...")
    fp_threshold, fp_threshold_stats = _tune_threshold_balanced(
        fp_model, X_va_fp, y_va_fp, 
        target_precision=0.60, target_recall=0.50
    )
    fp_metrics = evaluate(fp_model, X_te_fp, y_te_fp, threshold=fp_threshold)
    print(f"FP metrics (threshold={fp_threshold}):", fp_metrics)

    _log_mlflow("fp_model_xgb", {"n_estimators": 200, "max_depth": 5}, 
                {k: v for k, v in fp_metrics.items()}, fp_model)

    # ── Save artifacts ───────────────────────────────────────────────────
    _save_artifact(
        {"model": calibrated_fraud, "features": FRAUD_FEATURES, "metrics": fraud_metrics,
         "threshold": fraud_threshold, "version": "xgb-fraud-v2-calibrated", 
         "best_params": best_params_f},
        FRAUD_MODEL_PATH,
    )
    _save_artifact(
        {"model": calibrated_fraud, "features": FRAUD_FEATURES, "metrics": fraud_metrics,
         "threshold": fraud_threshold, "version": "xgb-fraud-v2-calibrated", 
         "best_params": best_params_f},
        FRAUD_CALIBRATED_PATH,
    )
    _save_artifact(
        {"model": calibrated_fraud, "features": FRAUD_FEATURES, "version": "shadow-v1"},
        FRAUD_SHADOW_PATH,
    )
    _save_artifact(
        {"model": fp_model, "features": FP_FEATURES, "metrics": fp_metrics,
         "threshold": fp_threshold, "version": "xgb-fp-v2"},
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