import csv
import pickle
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.ml.models import FraudModel, FPModel

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'ml' / 'data'
ARTIFACTS_DIR = BASE_DIR / 'ml' / 'artifacts'

_all_records = None
_models = None

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

def get_all_records():
    global _all_records
    if _all_records is None:
        _all_records = load_csv(DATA_DIR / 'full.csv')
    return _all_records

def get_models():
    global _models
    if _models is None:
        try:
            with open(ARTIFACTS_DIR / 'fraud_model.pkl', 'rb') as f:
                fraud = pickle.load(f)
            with open(ARTIFACTS_DIR / 'fp_model.pkl', 'rb') as f:
                fp = pickle.load(f)
            _models = {'fraud': fraud, 'fp': fp}
        except Exception:
            # Fallback for Railway/Linux
            from app.ml.train_models import evaluate, compute_fraud_score, compute_fp_score
            test = load_csv(DATA_DIR / 'test.csv')
            fraud_metrics = evaluate(test, compute_fraud_score, 'is_fraud')
            fp_metrics = evaluate(test, compute_fp_score, 'is_false_positive')
            _models = {
                'fraud': {'model': FraudModel(), 'features': list(test[0].keys()), 'metrics': fraud_metrics},
                'fp': {'model': FPModel(), 'features': list(test[0].keys()), 'metrics': fp_metrics}
            }
    return _models

@router.get('/transactions')
def list_transactions():
    records = get_all_records()
    txs = records[:100]
    return [{'id': t['transaction_id'], 'amount': t['amount'], 'is_fraud': t['is_fraud'],
             'is_flagged': t['is_flagged'], 'merchant_category': t['merchant_category']} for t in txs]

@router.get('/transactions/{tx_id}')
def get_transaction(tx_id: str):
    records = get_all_records()
    tx = next((r for r in records if r['transaction_id'] == tx_id), None)
    if not tx:
        raise HTTPException(404, 'Transaction not found')
    
    models = get_models()
    fraud_prob = float(models['fraud']['model'].predict_proba([tx])[0][1])
    fp_prob = float(models['fp']['model'].predict_proba([tx])[0][1])
    
    ltv = tx['customer_avg_tx_size'] * tx['customer_tx_count_30d'] * 6 * 0.7
    
    from app.services.strike_selector import calculate_action_losses, threshold_baseline_decision
    result = calculate_action_losses(fraud_prob, fp_prob, tx['amount'], ltv)
    baseline_action = threshold_baseline_decision(fraud_prob)
    baseline_loss = result['losses'][baseline_action]
    tiebreaker_loss = result['losses'][result['recommended_action']]
    savings = baseline_loss - tiebreaker_loss
    
    return {
        'transaction': tx,
        'fraud_prob': fraud_prob,
        'fp_prob': fp_prob,
        'ltv': ltv,
        'decision': result,
        'baseline_action': baseline_action,
        'baseline_loss': baseline_loss,
        'savings_vs_baseline': savings
    }
