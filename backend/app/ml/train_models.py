import csv
import pickle
import os
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score

from .models import FraudModel, FPModel, compute_fraud_score

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

FRAUD_FEATURES = [
    "amount", "velocity_1h", "velocity_24h", "device_change_flag",
    "geo_mismatch_flag", "is_cross_border", "hour_of_day",
    "customer_tenure_days", "customer_tx_count_30d", "customer_refund_rate"
]

FP_FEATURES = [
    "amount", "customer_tenure_days", "customer_tx_count_30d",
    "customer_refund_rate", "device_change_flag", "geo_mismatch_flag"
]

REVIEW_FEATURES = [
    "amount", "fraud_prob", "customer_tenure_days",
    "merchant_category_encoded", "hour_of_day"
]


def load_csv(filename):
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [{k: _cast(v) for k, v in row.items()} for row in reader]


def _cast(v):
    try:
        return int(v)
    except:
        try:
            return float(v)
        except:
            return v


def _encode_merchant(cat):
    mapping = {"Retail": 0, "SaaS": 1, "B2B": 2, "Food": 3}
    return mapping.get(cat, 0)


def extract_features(records, feature_names, for_review=False):
    X = []
    for r in records:
        row = []
        for f in feature_names:
            if f == "merchant_category_encoded":
                row.append(_encode_merchant(r.get("merchant_category", "Retail")))
            elif f == "fraud_prob":
                row.append(compute_fraud_score(r))
            else:
                row.append(r.get(f, 0))
        X.append(row)
    return X


def evaluate(records, score_fn, label_key):
    y_true = [r[label_key] for r in records]
    y_scores = [score_fn(r) for r in records]
    threshold = 0.5
    y_pred = [1 if s >= threshold else 0 for s in y_scores]

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    try:
        pr_auc = average_precision_score(y_true, y_scores)
    except:
        pr_auc = f1

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "pr_auc": round(pr_auc, 3),
    }


def train_fraud_model(train_records):
    X = extract_features(train_records, FRAUD_FEATURES)
    y = [r["is_fraud"] for r in train_records]
    model = GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
    model.fit(X, y)
    return model


def train_fp_model(train_records):
    X = extract_features(train_records, FP_FEATURES)
    y = [r["is_false_positive"] for r in train_records]
    model = GradientBoostingClassifier(n_estimators=80, max_depth=3, random_state=42)
    model.fit(X, y)
    return model


def train_review_model(train_records):
    X = extract_features(train_records, REVIEW_FEATURES, for_review=True)
    y = []
    for r in train_records:
        base = 2.0
        base += r["is_fraud"] * 3.5
        base += min(r["amount"] / 100000, 1.0) * 2.0
        base += (1 - min(r["customer_tenure_days"] / 1000, 1.0)) * 1.5
        y.append(base)
    model = LinearRegression()
    model.fit(X, y)
    return model


def evaluate_model(model, test_records, feature_names, label_key=None, is_regression=False):
    X = extract_features(test_records, feature_names)
    if is_regression:
        predictions = model.predict(X)
        return {
            "mean_prediction": round(sum(predictions) / len(predictions), 2),
            "min": round(min(predictions), 2),
            "max": round(max(predictions), 2),
        }

    y_true = [r[label_key] for r in test_records]
    y_pred = model.predict(X)

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    pr_auc = average_precision_score(y_true, model.predict_proba(X)[:, 1])

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "pr_auc": round(pr_auc, 3),
    }


if __name__ == "__main__":
    train = load_csv(DATA_DIR / "train.csv")
    test = load_csv(DATA_DIR / "test.csv")

    print("Training fraud model...")
    fraud_model = train_fraud_model(train)
    fraud_metrics = evaluate_model(fraud_model, test, FRAUD_FEATURES, "is_fraud")
    print("Fraud metrics:", fraud_metrics)

    print("Training FP model...")
    fp_model = train_fp_model(train)
    fp_metrics = evaluate_model(fp_model, test, FP_FEATURES, "is_false_positive")
    print("FP metrics:", fp_metrics)

    print("Training review time model...")
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

    print("All models saved to", ARTIFACTS_DIR)
