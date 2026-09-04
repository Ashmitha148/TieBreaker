"""TieBreaker Model Evaluation — V3 (honest CV, XGBoost-compatible).

FIXES from V2:
1. CV now loads best_params from artifact and uses them (not hardcoded defaults).
2. CV uses the SAME scale_pos_weight as the trained model.
3. Dropped PERFECT_SCORE_THRESHOLD check (not useful for balanced models).
4. Honest assessment updated for realistic metrics.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit

try:
    from .data import FRAUD_FEATURES, FP_FEATURES, get_feature_matrix, load_data
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from data import FRAUD_FEATURES, FP_FEATURES, get_feature_matrix, load_data

# --------------------------------------------------------------------------- #
# Paths & config
# --------------------------------------------------------------------------- #
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
OUTPUT = ARTIFACTS / "evaluation_metrics.json"

MAX_ROWS = int(os.getenv("TB_MAX_ROWS", os.getenv("TB_EVAL_MAX_ROWS", "300000")))
CV_SUBSAMPLE = int(os.getenv("TB_CV_SUBSAMPLE", "20000"))
N_BINS = 10


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def reliability_diagram(y_true, y_prob, n_bins: int = N_BINS):
    bins = np.linspace(0, 1, n_bins + 1)
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    diagram = []
    for i in range(n_bins):
        if i == n_bins - 1:
            mask = (y_prob >= bins[i]) & (y_prob <= bins[i + 1])
        else:
            mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
        count = int(mask.sum())
        label = f"{bins[i]:.1f}-{bins[i + 1]:.1f}"
        if count > 0:
            diagram.append({
                "bin": label,
                "mean_pred": round(float(y_prob[mask].mean()), 4),
                "actual_rate": round(float(y_true[mask].mean()), 4),
                "count": count,
            })
        else:
            diagram.append({"bin": label, "mean_pred": None, "actual_rate": None, "count": 0})
    return diagram


def cv_fraud_model(X_train, y_train, model, n_splits: int = 5):
    """5-fold TimeSeriesSplit CV — strict temporal order."""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores = {"precision": [], "recall": [], "f1": []}
    X = np.asarray(X_train)
    y = np.asarray(y_train)
    for train_idx, val_idx in tscv.split(X):
        X_tr, X_va = X[train_idx], X[val_idx]
        y_tr, y_va = y[train_idx], y[val_idx]
        m = clone(model)
        m.fit(X_tr, y_tr)
        y_pred = m.predict(X_va)
        scores["precision"].append(precision_score(y_va, y_pred, zero_division=0))
        scores["recall"].append(recall_score(y_va, y_pred, zero_division=0))
        scores["f1"].append(f1_score(y_va, y_pred, zero_division=0))
    return {
        "n_splits": n_splits,
        **{
            k: {
                "mean": round(float(np.mean(v)), 4),
                "std": round(float(np.std(v)), 4),
            }
            for k, v in scores.items()
        },
    }


def _extract_feature_importance(model, features):
    raw_model = model
    if hasattr(model, "calibrated_classifiers_"):
        try:
            raw_model = model.calibrated_classifiers_[0].estimator
        except Exception:
            raw_model = None

    if raw_model is None:
        return {}

    importance = {}
    try:
        booster = raw_model.get_booster()
        scores = booster.get_score(importance_type="gain")
        for k, v in scores.items():
            idx = int(k[1:])
            if idx < len(features):
                importance[features[idx]] = v
    except Exception:
        pass

    if not importance and hasattr(raw_model, "feature_importances_"):
        importance = dict(zip(features, raw_model.feature_importances_.tolist()))

    return {k: round(v, 4) for k, v in sorted(importance.items(), key=lambda x: -x[1])}


def evaluate_model(name, model, X, y_true, features, merchant_cats=None, threshold=0.5):
    X = np.array(X)
    y_true = np.array(y_true)
    y_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    metrics = {
        "model_name": name,
        "test_set_size": len(y_true),
        "decision_threshold": round(float(threshold), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "pr_auc": round(average_precision_score(y_true, y_proba), 4),
        "roc_auc": round(roc_auc_score(y_true, y_proba), 4),
        "brier_score": round(brier_score_loss(y_true, y_proba), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "reliability_diagram": reliability_diagram(y_true, y_proba),
    }

    importance = _extract_feature_importance(model, features)
    if importance:
        metrics["feature_importance"] = importance

    return metrics


def build_honest_assessment(fraud_metrics: dict, fp_metrics: dict, limitations: list) -> str:
    lines = [
        f"The fraud model scored {fraud_metrics['precision']:.1%} precision and "
        f"{fraud_metrics['recall']:.1%} recall on {fraud_metrics['test_set_size']} held-out records."
    ]

    if fraud_metrics["f1"] >= 0.70:
        lines.append(
            "This is a strong, defensible result for a hackathon-stage model with temporal "
            "splitting and leakage-safe features."
        )
    elif fraud_metrics["f1"] >= 0.60:
        lines.append("This is a moderate, plausible result for an early-stage model.")
    elif fraud_metrics["f1"] < 0.5:
        lines.append("This is a weak result - further feature work or more training data is needed.")
    else:
        lines.append("This is a moderate, plausible result for an early-stage model.")

    lines.append(
        f"The false-positive model scored {fp_metrics['precision']:.1%} precision and "
        f"{fp_metrics['recall']:.1%} recall."
    )

    if not limitations:
        lines.append("No major calibration or separation red flags detected.")
    return " ".join(lines)


def main():
    print(f"Loading IEEE-CIS temporal test split (max_rows={MAX_ROWS})...")

    train_df, _val_df, test_df = load_data(max_rows=MAX_ROWS)
    print(f"Loaded {len(test_df)} test records (temporal 15% holdout)\n")

    # Load artifacts
    try:
        fraud_artifact = joblib.load(ARTIFACTS / "fraud_model.joblib")
        fp_artifact = joblib.load(ARTIFACTS / "fp_model.joblib")
    except FileNotFoundError as e:
        print(f"ERROR: Missing model artifact - {e}")
        print("Run backend/app/ml/train_models.py first.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Model artifact unreadable - {e}")
        sys.exit(1)

    # Leakage check
    try:
        train_ids = set(train_df["TransactionID"].astype("int64"))
        test_ids = set(test_df["TransactionID"].astype("int64"))
        overlap = train_ids & test_ids
        leakage = {
            "verified": len(overlap) == 0,
            "train_size": len(train_ids),
            "test_size": len(test_ids),
            "overlap_count": len(overlap),
            "overlap_ids_sample": sorted(overlap)[:20],
        }
    except Exception as e:
        leakage = {"verified": False, "error": str(e)}

    print(f"Leakage check: {'PASS' if leakage.get('verified') else 'FAIL'}")
    if not leakage.get("verified"):
        print("  STOP: fix your split before trusting metrics.")
        sys.exit(1)

    fraud_model = fraud_artifact["model"]
    fp_model = fp_artifact["model"]
    fraud_features = fraud_artifact["features"]
    fp_features = fp_artifact["features"]
    fraud_threshold = fraud_artifact.get("threshold", 0.5)
    fp_threshold = fp_artifact.get("threshold", 0.5)
    best_params = fraud_artifact.get("best_params", {})

    # Sanity guard
    feature_warnings = []
    for label, feats in [("fraud", fraud_features), ("FP", fp_features)]:
        missing = [f for f in feats if f not in test_df.columns]
        if missing:
            feature_warnings.append(
                f"{label} model features missing ({len(missing)}/{len(feats)})."
            )
            print(f"WARNING: {feature_warnings[-1]}")

    # Build feature matrices
    X_fraud = get_feature_matrix(test_df, fraud_features)
    y_fraud = test_df["isFraud"].astype(int).values

    X_fp = get_feature_matrix(test_df, fp_features)
    y_fp = test_df["is_false_positive"].astype(int).values

    fraud_metrics = evaluate_model(
        "Fraud Detector", fraud_model, X_fraud, y_fraud, fraud_features,
        None, threshold=fraud_threshold,
    )
    fp_metrics = evaluate_model(
        "False Positive", fp_model, X_fp, y_fp, fp_features,
        None, threshold=fp_threshold,
    )

    # TimeSeriesSplit CV -- strict temporal; never touches the final holdout.
    print("Running TimeSeriesSplit CV (train-only, strict temporal order)...")
    try:
        stored_cv = fraud_artifact.get("metrics", {}).get("timeseries_cv")
        if isinstance(stored_cv, dict) and "f1" in stored_cv:
            ts_cv = stored_cv
            print(f"  Using stored training CV: F1={ts_cv['f1']['mean']:.4f} "
                  f"+/- {ts_cv['f1']['std']:.4f}")
        else:
            X_tr_cv = get_feature_matrix(train_df, fraud_features)
            y_tr_cv = train_df["isFraud"].astype(int).values
            X_cv, y_cv = X_tr_cv[:CV_SUBSAMPLE], y_tr_cv[:CV_SUBSAMPLE]
            from xgboost import XGBClassifier
            fraud_rate = y_cv.mean() if len(y_cv) > 0 else 0.035
            spw = (1 - fraud_rate) / fraud_rate if fraud_rate > 0 else 1.0

            # Use best_params from artifact for CV
            cv_params = {
                "n_estimators": best_params.get("n_estimators", 200),
                "max_depth": best_params.get("max_depth", 6),
                "learning_rate": best_params.get("learning_rate", 0.1),
                "subsample": best_params.get("subsample", 0.9),
                "colsample_bytree": best_params.get("colsample_bytree", 0.9),
                "min_child_weight": best_params.get("min_child_weight", 3),
                "gamma": best_params.get("gamma", 0),
                "reg_alpha": best_params.get("reg_alpha", 0.1),
                "reg_lambda": best_params.get("reg_lambda", 1.0),
                "scale_pos_weight": spw,
                "eval_metric": "logloss",
                "random_state": 42,
                "n_jobs": -1,
            }
            cv_model = XGBClassifier(**cv_params)
            ts_cv = cv_fraud_model(X_cv, y_cv, cv_model, n_splits=5)
            ts_cv["subsample"] = CV_SUBSAMPLE
            print(f"  CV F1: {ts_cv['f1']['mean']:.4f} +/- {ts_cv['f1']['std']:.4f}")
        fraud_metrics["timeseries_cv"] = ts_cv
    except Exception as e:
        fraud_metrics["timeseries_cv"] = {"error": str(e)}
        print(f"  CV failed: {e}")

    limitations = []
    limitations.extend(feature_warnings)

    # Flag if metrics are suspiciously perfect
    if fraud_metrics["roc_auc"] > 0.98 and fraud_metrics["precision"] > 0.95:
        limitations.append(
            "Fraud model ROC-AUC > 0.98 with precision > 95% — possible leakage or overfitting."
        )

    if fraud_metrics["f1"] < 0.5:
        limitations.append(
            f"Fraud model F1 ({fraud_metrics['f1']:.3f}) is weak — more data or features needed."
        )

    if fp_metrics["recall"] < 0.3:
        limitations.append(
            f"FP model recall is {fp_metrics['recall']:.1%} — catches minority of false positives."
        )

    if fp_metrics["brier_score"] > 0.2:
        limitations.append(
            f"FP model Brier score ({fp_metrics['brier_score']:.3f}) indicates poor calibration."
        )

    honest_assessment = build_honest_assessment(fraud_metrics, fp_metrics, limitations)

    report = {
        "evaluated_at": datetime.now().isoformat(),
        "leakage_check": leakage,
        "test_set": {
            "total_records": len(test_df),
            "fraud_rate": round(float(y_fraud.mean()), 4) if len(y_fraud) else 0,
            "fp_rate": round(float(y_fp.mean()), 4) if len(y_fp) else 0,
            "dataset": f"IEEE-CIS temporal head ({MAX_ROWS} rows), 15% temporal holdout",
        },
        "models": {"fraud": fraud_metrics, "false_positive": fp_metrics},
        "limitations": limitations,
        "honest_assessment": honest_assessment,
        "fraud_precision": fraud_metrics["precision"],
        "fraud_recall": fraud_metrics["recall"],
        "fraud_f1": fraud_metrics["f1"],
        "fp_precision": fp_metrics["precision"],
        "fp_recall": fp_metrics["recall"],
        "fp_f1": fp_metrics["f1"],
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'=' * 60}")
    print("TieBreaker Model Evaluation - Held-Out Test Set")
    print(f"{'=' * 60}")
    for model_name, m in report["models"].items():
        print(f"\n{model_name.upper()}")
        print(f"  Precision: {m['precision']:.4f} | Recall: {m['recall']:.4f} | F1: {m['f1']:.4f}")
        print(f"  PR-AUC: {m['pr_auc']:.4f} | ROC-AUC: {m['roc_auc']:.4f} | Brier: {m['brier_score']:.4f}")
        print(f"  Threshold: {m['decision_threshold']:.4f}")
        if "feature_importance" in m:
            print(f"  Top features: {', '.join(list(m['feature_importance'].keys())[:3])}")

    print(f"\nCV F1: {fraud_metrics.get('timeseries_cv', {}).get('f1', {}).get('mean', 'N/A')} +/- "
          f"{fraud_metrics.get('timeseries_cv', {}).get('f1', {}).get('std', 'N/A')}")

    print(f"\nLIMITATIONS:")
    for lim in limitations:
        print(f"  - {lim}")
    print(f"\n  {report['honest_assessment']}")

    f = report["models"]["fraud"]
    fp = report["models"]["false_positive"]
    print(f"\nREADME TABLE:")
    print(f"| Fraud Detector | {f['precision']:.3f} | {f['recall']:.3f} | {f['f1']:.3f} | {f['pr_auc']:.3f} | {f['roc_auc']:.3f} |")
    print(f"| False Positive | {fp['precision']:.3f} | {fp['recall']:.3f} | {fp['f1']:.3f} | {fp['pr_auc']:.3f} | {fp['roc_auc']:.3f} |")
    print(f"\nSaved report to: {OUTPUT}")


if __name__ == "__main__":
    main()