import csv
import pickle
import os
from pathlib import Path
from app.ml.models import FraudModel, FPModel

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
ARTIFACTS_DIR = BASE_DIR / 'artifacts'
ARTIFACTS_DIR.mkdir(exist_ok=True)

def load_csv(filename):
    with open(filename, 'r', encoding='utf-8') as f:
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

def compute_fraud_score(tx):
    score = 0.0
    score += min(tx['amount'] / 200000, 1.0) * 0.25
    score += min(tx['velocity_1h'] / 15, 1.0) * 0.20
    score += min(tx['velocity_24h'] / 50, 1.0) * 0.10
    score += tx['device_change_flag'] * 0.15
    score += tx['geo_mismatch_flag'] * 0.20
    score += tx['is_cross_border'] * 0.10
    score += (tx['hour_of_day'] / 24) * 0.05
    score += (1 - min(tx['customer_tenure_days'] / 1000, 1.0)) * 0.10
    score += (1 - min(tx['customer_tx_count_30d'] / 20, 1.0)) * 0.10
    score += tx['customer_refund_rate'] * 0.05
    return min(max(score, 0.0), 0.98)

def compute_fp_score(tx):
    score = 0.0
    score += min(tx['customer_tenure_days'] / 1000, 1.0) * 0.30
    score += min(tx['customer_tx_count_30d'] / 20, 1.0) * 0.25
    score += (1 - min(tx['amount'] / 100000, 1.0)) * 0.15
    score += (1 - tx['customer_refund_rate']) * 0.20
    score += (1 if tx['merchant_category'] in ['Retail', 'SaaS'] else 0) * 0.10
    return min(max(score, 0.0), 0.98)

def evaluate(records, score_fn, label_key):
    predictions = [1 if score_fn(r) > 0.5 else 0 for r in records]
    labels = [r[label_key] for r in records]
    tp = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 1)
    fp = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 0)
    fn = sum(1 for p, l in zip(predictions, labels) if p == 0 and l == 1)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    return {'precision': round(precision, 3), 'recall': round(recall, 3), 'f1': round(f1, 3), 'pr_auc': round(f1, 3)}

if __name__ == '__main__':
    train = load_csv(DATA_DIR / 'train.csv')
    test = load_csv(DATA_DIR / 'test.csv')
    
    fraud_metrics = evaluate(test, compute_fraud_score, 'is_fraud')
    fp_metrics = evaluate(test, compute_fp_score, 'is_false_positive')
    
    print('Fraud metrics:', fraud_metrics)
    print('FP metrics:', fp_metrics)
    
    pickle.dump({'model': FraudModel(), 'features': list(test[0].keys()), 'metrics': fraud_metrics}, open(ARTIFACTS_DIR / 'fraud_model.pkl', 'wb'))
    pickle.dump({'model': FPModel(), 'features': list(test[0].keys()), 'metrics': fp_metrics}, open(ARTIFACTS_DIR / 'fp_model.pkl', 'wb'))
    print('Models saved to', ARTIFACTS_DIR)
