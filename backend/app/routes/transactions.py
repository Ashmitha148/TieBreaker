import csv
import pickle
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ml.models import FraudModel, FPModel
from ..database import get_db
from ..models import Decision, Override, AuditLog

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
            from ..ml.train_models import evaluate
            from ..ml.models import compute_fraud_score, compute_fp_score
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
def get_transaction(tx_id: str, db: Session = Depends(get_db)):
    records = get_all_records()
    tx = next((r for r in records if r['transaction_id'] == tx_id), None)
    if not tx:
        raise HTTPException(404, 'Transaction not found')
    
    models = get_models()
    fraud_prob = float(models['fraud']['model'].predict_proba([tx])[0][1])
    fp_prob = float(models['fp']['model'].predict_proba([tx])[0][1])
    
    ltv = tx['customer_avg_tx_size'] * tx['customer_tx_count_30d'] * 6 * 0.7
    
    from ..services.strike_selector import calculate_action_losses, threshold_baseline_decision
    result = calculate_action_losses(fraud_prob, fp_prob, tx['amount'], ltv)
    baseline_action = threshold_baseline_decision(fraud_prob)
    baseline_loss = result['losses'][baseline_action]
    tiebreaker_loss = result['losses'][result['recommended_action']]
    savings = baseline_loss - tiebreaker_loss
    
    decision = Decision(
        transaction_id=tx_id,
        fraud_prob=fraud_prob,
        fp_prob=fp_prob,
        amount=tx['amount'],
        ltv=ltv,
        recommended_action=result['recommended_action'],
        baseline_action=baseline_action,
        savings_vs_baseline=savings,
        is_counterintuitive=result.get('is_counterintuitive', False),
    )
    db.add(decision)
    db.commit()
    
    override = db.query(Override).filter(Override.transaction_id == tx_id).order_by(Override.created_at.desc()).first()
    drivers = _compute_drivers(tx, fraud_prob, fp_prob)
    
    return {
        'transaction': tx,
        'fraud_prob': fraud_prob,
        'fp_prob': fp_prob,
        'ltv': ltv,
        'decision': result,
        'baseline_action': baseline_action,
        'baseline_loss': baseline_loss,
        'savings_vs_baseline': savings,
        'override': {
            'action': override.overridden_action,
            'reason': override.reason,
            'analyst': override.analyst_id,
        } if override else None,
        'drivers': drivers,
    }


class OverrideRequest(BaseModel):
    action: str
    reason: str
    analyst_id: str = "analyst_001"


@router.post('/transactions/{tx_id}/override')
def create_override(tx_id: str, req: OverrideRequest, db: Session = Depends(get_db)):
    records = get_all_records()
    tx = next((r for r in records if r['transaction_id'] == tx_id), None)
    if not tx:
        raise HTTPException(404, 'Transaction not found')
    
    models = get_models()
    fraud_prob = float(models['fraud']['model'].predict_proba([tx])[0][1])
    fp_prob = float(models['fp']['model'].predict_proba([tx])[0][1])
    ltv = tx['customer_avg_tx_size'] * tx['customer_tx_count_30d'] * 6 * 0.7
    
    from ..services.strike_selector import calculate_action_losses
    result = calculate_action_losses(fraud_prob, fp_prob, tx['amount'], ltv)
    
    decision = db.query(Decision).filter(Decision.transaction_id == tx_id).order_by(Decision.created_at.desc()).first()
    if not decision:
        decision = Decision(
            transaction_id=tx_id,
            fraud_prob=fraud_prob,
            fp_prob=fp_prob,
            amount=tx['amount'],
            ltv=ltv,
            recommended_action=result['recommended_action'],
            baseline_action=result['recommended_action'],
            savings_vs_baseline=0,
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
    
    override = Override(
        decision_id=decision.id,
        transaction_id=tx_id,
        original_action=result['recommended_action'],
        overridden_action=req.action,
        reason=req.reason,
        analyst_id=req.analyst_id,
    )
    db.add(override)
    
    audit = AuditLog(
        user=req.analyst_id,
        action="OVERRIDE",
        entity_type="transaction",
        entity_id=tx_id,
        details=f"Overridden from {result['recommended_action']} to {req.action}. Reason: {req.reason}",
    )
    db.add(audit)
    db.commit()
    
    return {
        'status': 'overridden',
        'transaction_id': tx_id,
        'original_action': result['recommended_action'],
        'new_action': req.action,
        'reason': req.reason,
    }


def _compute_drivers(tx, fraud_prob, fp_prob):
    drivers = []
    
    amount_ratio = min(tx['amount'] / 200000, 1.0)
    if amount_ratio > 0.5:
        drivers.append({
            'feature': 'Transaction Amount',
            'value': f"â‚¹{tx['amount']:,.0f}",
            'impact': 'high' if amount_ratio > 0.8 else 'medium',
            'direction': 'increases risk' if tx['amount'] > 50000 else 'neutral',
            'contribution': round(amount_ratio * 0.25, 3),
        })
    
    if tx['velocity_1h'] > 5:
        drivers.append({
            'feature': 'Velocity (1h)',
            'value': f"{tx['velocity_1h']} txns",
            'impact': 'high' if tx['velocity_1h'] > 10 else 'medium',
            'direction': 'increases risk',
            'contribution': round(min(tx['velocity_1h'] / 15, 1.0) * 0.20, 3),
        })
    
    if tx['geo_mismatch_flag']:
        drivers.append({
            'feature': 'Geo Mismatch',
            'value': 'Yes',
            'impact': 'high',
            'direction': 'increases risk',
            'contribution': 0.20,
        })
    
    if tx['device_change_flag']:
        drivers.append({
            'feature': 'Device Change',
            'value': 'Yes',
            'impact': 'medium',
            'direction': 'increases risk',
            'contribution': 0.15,
        })
    
    if tx['customer_tenure_days'] > 365:
        drivers.append({
            'feature': 'Customer Tenure',
            'value': f"{tx['customer_tenure_days']} days",
            'impact': 'medium',
            'direction': 'decreases risk',
            'contribution': round(-0.1 * min(tx['customer_tenure_days'] / 1000, 1.0), 3),
        })
    
    if tx['customer_avg_tx_size'] * tx['customer_tx_count_30d'] > 50000:
        drivers.append({
            'feature': 'Customer Value',
            'value': f"â‚¹{tx['customer_avg_tx_size'] * tx['customer_tx_count_30d']:,.0f}/mo",
            'impact': 'high',
            'direction': 'decreases risk',
            'contribution': round(-0.15, 3),
        })
    
    drivers.sort(key=lambda x: abs(x['contribution']), reverse=True)
    return drivers[:3]
