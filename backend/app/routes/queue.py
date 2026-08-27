from fastapi import APIRouter
from app.routes.transactions import get_all_records, get_models
from app.services.strike_selector import calculate_action_losses

router = APIRouter()

@router.get('/queue')
def get_queue(limit: int = 20):
    records = get_all_records()[:200]
    models = get_models()
    ranked = []
    
    for tx in records:
        if tx['is_flagged'] == 0:
            continue
        fraud_prob = float(models['fraud']['model'].predict_proba([tx])[0][1])
        fp_prob = float(models['fp']['model'].predict_proba([tx])[0][1])
        ltv = tx['customer_avg_tx_size'] * tx['customer_tx_count_30d'] * 6 * 0.7
        result = calculate_action_losses(fraud_prob, fp_prob, tx['amount'], ltv)
        impact = result['losses']['ALLOW'] - result['losses'][result['recommended_action']]
        
        ranked.append({
            'transaction_id': tx['transaction_id'],
            'amount': tx['amount'],
            'merchant_category': tx['merchant_category'],
            'fraud_prob': round(fraud_prob, 3),
            'expected_loss': result['losses'][result['recommended_action']],
            'impact_score': round(impact, 2),
            'recommended_action': result['recommended_action'],
            'review_time': 4.2
        })
    
    ranked.sort(key=lambda x: x['impact_score'], reverse=True)
    return {'queue': ranked[:limit], 'total': len(ranked), 'analysts_online': 12, 'capacity': 50}

@router.post('/queue/reorder')
def reorder_queue(priority: str = 'impact'):
    return {'status': 'reordered', 'priority': priority}
