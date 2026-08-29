"""
TieBreaker Model Evaluation — Held-Out Test Set
Run this to generate the exact precision/recall numbers for your README.
"""

import csv
import pickle
from pathlib import Path

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
)

# Paths
ROOT = Path(__file__).parent.parent / "backend" / "app" / "ml"
ARTIFACTS = ROOT / "artifacts"
DATA = ROOT / "data"


def load_csv(filename: str):
    with open(DATA / filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            parsed = {}
            for k, v in row.items():
                if v.isdigit():
                    parsed[k] = int(v)
                else:
                    try:
                        parsed[k] = float(v)
                    except ValueError:
                        parsed[k] = v
            rows.append(parsed)
        return rows


def evaluate():
    test = load_csv("test.csv")
    print(f"Loaded {len(test)} test records")

    # Load artifacts
    with open(ARTIFACTS / "fraud_model.pkl", "rb") as f:
        fraud_artifact = pickle.load(f)
    with open(ARTIFACTS / "fp_model.pkl", "rb") as f:
        fp_artifact = pickle.load(f)

    fraud_model = fraud_artifact["model"]
    fp_model = fp_artifact["model"]
    fraud_features = fraud_artifact["features"]
    fp_features = fp_artifact["features"]

    # --- Fraud Model ---
    X_fraud = [[r[f] for f in fraud_features] for r in test]
    y_fraud_true = [int(r["is_fraud"]) for r in test]
    y_fraud_pred = fraud_model.predict(X_fraud)
    y_fraud_proba = fraud_model.predict_proba(X_fraud)[:, 1]

    fraud_precision = precision_score(y_fraud_true, y_fraud_pred, zero_division=0)
    fraud_recall = recall_score(y_fraud_true, y_fraud_pred, zero_division=0)
    fraud_f1 = f1_score(y_fraud_true, y_fraud_pred, zero_division=0)
    fraud_pr_auc = average_precision_score(y_fraud_true, y_fraud_proba)

    print("\n" + "=" * 50)
    print("FRAUD MODEL — Held-Out Test Set")
    print("=" * 50)
    print(f"Precision:  {fraud_precision:.4f}")
    print(f"Recall:     {fraud_recall:.4f}")
    print(f"F1-Score:   {fraud_f1:.4f}")
    print(f"PR-AUC:     {fraud_pr_auc:.4f}")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_fraud_true, y_fraud_pred))
    print("\nClassification Report:")
    print(classification_report(y_fraud_true, y_fraud_pred, target_names=["Legit", "Fraud"]))

    # --- False Positive Model ---
    X_fp = [[r[f] for f in fp_features] for r in test]
    y_fp_true = [int(r["is_false_positive"]) for r in test]
    y_fp_pred = fp_model.predict(X_fp)
    y_fp_proba = fp_model.predict_proba(X_fp)[:, 1]

    fp_precision = precision_score(y_fp_true, y_fp_pred, zero_division=0)
    fp_recall = recall_score(y_fp_true, y_fp_pred, zero_division=0)
    fp_f1 = f1_score(y_fp_true, y_fp_pred, zero_division=0)
    fp_pr_auc = average_precision_score(y_fp_true, y_fp_proba)

    print("\n" + "=" * 50)
    print("FALSE POSITIVE MODEL — Held-Out Test Set")
    print("=" * 50)
    print(f"Precision:  {fp_precision:.4f}")
    print(f"Recall:     {fp_recall:.4f}")
    print(f"F1-Score:   {fp_f1:.4f}")
    print(f"PR-AUC:     {fp_pr_auc:.4f}")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_fp_true, y_fp_pred))
    print("\nClassification Report:")
    print(classification_report(y_fp_true, y_fp_pred, target_names=["Not FP", "False Positive"]))

    # --- Export for README ---
    print("\n" + "=" * 50)
    print("COPY-PASTE FOR README")
    print("=" * 50)
    print(f"| Fraud Detector | {fraud_precision:.3f} | {fraud_recall:.3f} | {fraud_f1:.3f} | {fraud_pr_auc:.3f} |")
    print(f"| False Positive | {fp_precision:.3f} | {fp_recall:.3f} | {fp_f1:.3f} | {fp_pr_auc:.3f} |")

    # Save to JSON for backend to serve
    import json
    metrics = {
        "fraud": {
            "precision": round(fraud_precision, 4),
            "recall": round(fraud_recall, 4),
            "f1": round(fraud_f1, 4),
            "pr_auc": round(fraud_pr_auc, 4),
        },
        "false_positive": {
            "precision": round(fp_precision, 4),
            "recall": round(fp_recall, 4),
            "f1": round(fp_f1, 4),
            "pr_auc": round(fp_pr_auc, 4),
        },
        "test_set_size": len(test),
        "evaluated_at": __import__("datetime").datetime.now().isoformat(),
    }
    with open(ARTIFACTS / "evaluation_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved to {ARTIFACTS / 'evaluation_metrics.json'}")


if __name__ == "__main__":
    evaluate()