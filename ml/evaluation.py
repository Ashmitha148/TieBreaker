"""
TieBreaker Model Evaluation — Comprehensive Held-Out Test Set Analysis
Generates precision/recall, per-merchant breakdown, feature importance,
and calibration metrics. Outputs JSON for backend consumption.

FIXED VERSION — changes from original:
  1. honest_assessment is now generated FROM the real metrics, not hardcoded.
  2. "Suspiciously perfect" check now fires above 0.97, not only at exactly 1.0.
  3. CSV numeric parsing no longer mis-casts negative integers as floats.
"""

import csv
import joblib
import json
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
    classification_report,
)

# Paths
ROOT = Path(__file__).parent.parent / "backend" / "app" / "ml"
ARTIFACTS = ROOT / "artifacts"
DATA = ROOT / "data"
OUTPUT = ARTIFACTS / "evaluation_metrics.json"

PERFECT_SCORE_THRESHOLD = 0.97  # fixed: was only checking == 1.0


def _parse_value(v: str):
    """Fixed: str.isdigit() returns False for negative numbers, so
    '-5'.isdigit() is False and it used to fall through to float().
    This version checks properly signed ints first."""
    v = v.strip()
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def load_csv(filename: str):
    with open(DATA / filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            parsed = {k: _parse_value(v) for k, v in row.items()}
            rows.append(parsed)
        return rows


def verify_no_leakage(train_path: Path, test_path: Path, id_col: str = "transaction_id"):
    """Confirms train and test sets don't share transaction IDs. Without this,
    a judge asking 'how do you know your test set wasn't seen during training'
    has no answer other than 'trust me' — this makes it checkable."""
    try:
        train = load_csv(train_path.name)
        test = load_csv(test_path.name)
        def _ids(rows):
            found = set()
            for r in rows:
                raw = r.get(id_col)
                if raw is None or raw == "":
                    raw = r.get("id", "")
                value = str(raw).strip()
                if value:
                    found.add(value)
            return found

        train_ids = _ids(train)
        test_ids = _ids(test)
        if not train_ids or not test_ids:
            return {
                "verified": False,
                "error": f"Could not read {id_col} (or id) from train/test CSVs — leakage cannot be verified.",
                "train_size": len(train_ids),
                "test_size": len(test_ids),
                "overlap_count": 0,
            }
        overlap = train_ids & test_ids
        return {
            "verified": len(overlap) == 0,
            "train_size": len(train_ids),
            "test_size": len(test_ids),
            "overlap_count": len(overlap),
            "overlap_ids_sample": sorted(list(overlap))[:20],
        }
    except Exception as e:
        return {"verified": False, "error": str(e)}


def evaluate_model(name, model, X, y_true, features, merchant_cats=None):
    """Full evaluation with calibration and per-merchant breakdown."""
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]

    metrics = {
        "model_name": name,
        "test_set_size": len(y_true),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "pr_auc": round(average_precision_score(y_true, y_proba), 4),
        "roc_auc": round(roc_auc_score(y_true, y_proba), 4),
        "brier_score": round(brier_score_loss(y_true, y_proba), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }

    if hasattr(model, "feature_importances_"):
        importance = dict(zip(features, model.feature_importances_.tolist()))
        metrics["feature_importance"] = {
            k: round(v, 4) for k, v in sorted(importance.items(), key=lambda x: -x[1])
        }

    if merchant_cats:
        per_merchant = {}
        for cat in set(merchant_cats):
            mask = [m == cat for m in merchant_cats]
            y_cat = [y for y, m in zip(y_true, mask) if m]
            p_cat = [p for p, m in zip(y_pred, mask) if m]

            if len(set(y_cat)) > 1:
                per_merchant[cat] = {
                    "count": len(y_cat),
                    "precision": round(precision_score(y_cat, p_cat, zero_division=0), 4),
                    "recall": round(recall_score(y_cat, p_cat, zero_division=0), 4),
                    "f1": round(f1_score(y_cat, p_cat, zero_division=0), 4),
                }
            else:
                per_merchant[cat] = {
                    "count": len(y_cat),
                    "note": "Only one class present in test set",
                }
        metrics["per_merchant"] = per_merchant

    return metrics


def build_honest_assessment(fraud_metrics: dict, fp_metrics: dict, limitations: list) -> str:
    """FIXED: this used to be a hardcoded string that always described the
    same outcome regardless of what the models actually did. Now it's built
    from the real numbers so it can never misrepresent a real run."""
    lines = []

    fp_p, fr_p = fraud_metrics["precision"], fraud_metrics["recall"]
    lines.append(
        f"The fraud model scored {fraud_metrics['precision']:.1%} precision and "
        f"{fraud_metrics['recall']:.1%} recall on {fraud_metrics['test_set_size']} held-out records."
    )

    if fraud_metrics["precision"] >= PERFECT_SCORE_THRESHOLD and fraud_metrics["recall"] >= PERFECT_SCORE_THRESHOLD:
        lines.append(
            "This near-perfect separation is expected on engineered synthetic features and should not be "
            "read as production performance — real traffic has label noise, adversarial adaptation, and "
            "distribution shift that synthetic data does not capture."
        )
    elif fraud_metrics["f1"] < 0.5:
        lines.append(
            "This is a weak result — the fraud model is not yet reliable enough to act on autonomously "
            "and would need further feature work or more training data before production use."
        )
    else:
        lines.append("This is a moderate, plausible result for an early-stage model on synthetic data.")

    lines.append(
        f"The false-positive model scored {fp_metrics['precision']:.1%} precision and "
        f"{fp_metrics['recall']:.1%} recall — "
        + (
            "predicting which legitimate transactions will look risky is inherently harder than detecting "
            "fraud itself, since legitimate behavior has far higher variance."
            if fp_metrics["recall"] < fraud_metrics["recall"]
            else "this model is currently performing comparably to the fraud model, which is worth double-checking "
            "for data leakage between the two targets."
        )
    )

    if not limitations:
        lines.append("No major calibration or separation red flags were detected in this run.")

    return " ".join(lines)


def main():
    test = load_csv("test.csv")
    print(f"Loaded {len(test)} test records\n")

       try:
        with open(ARTIFACTS / "fraud_model.joblib", "rb") as f:
            fraud_artifact = joblib.load(f)
        with open(ARTIFACTS / "fp_model.joblib", "rb") as f:
            fp_artifact = joblib.load(f)
    except FileNotFoundError as e:
        print(f"ERROR: Missing model artifact — {e}")
        print("Run backend/app/ml/train_models.py first to generate fraud_model.joblib and fp_model.joblib")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Model artifact is corrupt or unreadable — {e}")
        sys.exit(1)

    leakage = verify_no_leakage(DATA / "train.csv", DATA / "test.csv")
    print(f"\nLeakage check: {'PASS' if leakage.get('verified') else 'FAIL'}")
    if leakage.get("verified"):
        print(f"  train={leakage['train_size']} test={leakage['test_size']} overlap={leakage['overlap_count']}")
    elif "error" in leakage:
        print(f"  Could not verify: {leakage['error']}")
        print("  STOP: refusing to publish metrics without a verifiable train/test split.")
        sys.exit(1)
    else:
        print(f"  FAIL — {leakage['overlap_count']} overlapping transaction IDs between train and test.")
        if leakage.get("overlap_ids_sample"):
            print(f"  Sample overlap IDs: {leakage['overlap_ids_sample']}")
        print("  STOP: fix your split before trusting any metric below — your test set is contaminated.")
        sys.exit(1)


    fraud_model = fraud_artifact["model"]
    fp_model = fp_artifact["model"]
    fraud_features = fraud_artifact["features"]
    fp_features = fp_artifact["features"]

    X_fraud = [[r[f] for f in fraud_features] for r in test]
    y_fraud = [int(r["is_fraud"]) for r in test]
    merchant_cats = [r.get("merchant_category", "Unknown") for r in test]

    X_fp = [[r[f] for f in fp_features] for r in test]
    y_fp = [int(r["is_false_positive"]) for r in test]

    fraud_metrics = evaluate_model("Fraud Detector", fraud_model, X_fraud, y_fraud, fraud_features, merchant_cats)
    fp_metrics = evaluate_model("False Positive", fp_model, X_fp, y_fp, fp_features, merchant_cats)

    limitations = []

    if fraud_metrics["precision"] >= PERFECT_SCORE_THRESHOLD and fraud_metrics["recall"] >= PERFECT_SCORE_THRESHOLD:
        limitations.append(
            f"Fraud model precision/recall are both >= {PERFECT_SCORE_THRESHOLD:.0%} on synthetic data — "
            "real-world performance will degrade due to distribution shift, adversarial patterns, and label noise. "
            "This score reflects clean synthetic features, not production reality."
        )

    if fp_metrics["recall"] < 0.3:
        limitations.append(
            f"FP model recall is {fp_metrics['recall']:.1%} — it catches only a minority of false positives. "
            "This is expected: false positives are inherently harder to predict than fraud (legitimate transactions "
            "have high variance). In production, this would be improved with merchant-specific features and "
            "behavioral biometrics."
        )

    if fp_metrics["brier_score"] > 0.2:
        limitations.append(
            f"FP model Brier score ({fp_metrics['brier_score']:.3f}) indicates poor probability calibration. "
            "Cost optimization depends on well-calibrated probabilities — this is a priority for v2."
        )

    honest_assessment = build_honest_assessment(fraud_metrics, fp_metrics, limitations)

    report = {
        "evaluated_at": datetime.now().isoformat(),
        "leakage_check": leakage,
        "test_set": {
            "total_records": len(test),
            "fraud_rate": round(sum(y_fraud) / len(y_fraud), 4),
            "fp_rate": round(sum(y_fp) / len(y_fp), 4),
            "merchant_distribution": {cat: merchant_cats.count(cat) for cat in set(merchant_cats)},
        },
        "models": {
            "fraud": fraud_metrics,
            "false_positive": fp_metrics,
        },
        "limitations": limitations,
        "honest_assessment": honest_assessment,
    }

    with open(OUTPUT, "w") as f:
        json.dump(report, f, indent=2)

    print("=" * 60)
    print("TieBreaker Model Evaluation — Held-Out Test Set")
    print("=" * 60)
    print(f"\nTest Set: {report['test_set']['total_records']} records")
    print(f"Fraud Rate: {report['test_set']['fraud_rate']:.1%}")
    print(f"FP Rate: {report['test_set']['fp_rate']:.1%}")

    for model_name, m in report["models"].items():
        print(f"\n{'—' * 60}")
        print(f"{model_name.upper()}")
        print(f"{'—' * 60}")
        print(f"  Precision:  {m['precision']:.4f}")
        print(f"  Recall:     {m['recall']:.4f}")
        print(f"  F1-Score:   {m['f1']:.4f}")
        print(f"  PR-AUC:     {m['pr_auc']:.4f}")
        print(f"  ROC-AUC:    {m['roc_auc']:.4f}")
        print(f"  Brier:      {m['brier_score']:.4f}")
        print(f"  Confusion:  {m['confusion_matrix']}")
        if "feature_importance" in m:
            print(f"\n  Top Features:")
            for feat, imp in list(m["feature_importance"].items())[:5]:
                print(f"    {feat}: {imp:.4f}")
        if "per_merchant" in m:
            print(f"\n  Per-Merchant F1:")
            for cat, stats in m["per_merchant"].items():
                if "f1" in stats:
                    print(f"    {cat}: {stats['f1']:.3f} (n={stats['count']})")

    print(f"\n{'=' * 60}")
    print("LIMITATIONS & HONEST ASSESSMENT")
    print(f"{'=' * 60}")
    for lim in limitations:
        print(f"\n  • {lim}")
    print(f"\n  {report['honest_assessment']}")

    print(f"\n{'=' * 60}")
    print("COPY-PASTE FOR README (use these EXACT numbers, don't round further)")
    print(f"{'=' * 60}")
    f = report["models"]["fraud"]
    fp = report["models"]["false_positive"]
    print(f"| Fraud Detector | {f['precision']:.3f} | {f['recall']:.3f} | {f['f1']:.3f} | {f['pr_auc']:.3f} | {f['roc_auc']:.3f} |")
    print(f"| False Positive | {fp['precision']:.3f} | {fp['recall']:.3f} | {fp['f1']:.3f} | {fp['pr_auc']:.3f} | {fp['roc_auc']:.3f} |")

    print(f"\nSaved full report to: {OUTPUT}")


if __name__ == "__main__":
    main()
    