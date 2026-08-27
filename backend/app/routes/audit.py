from fastapi import APIRouter
from datetime import datetime, timedelta
import random

router = APIRouter()

@router.get('/audit')
def get_audit(limit: int = 50):
    actions = ['DECISION', 'OVERRIDE', 'CONFIG_CHANGE', 'MODEL_UPDATE']
    users = ['system', 'analyst_001', 'analyst_002', 'admin']
    reasons = [
        'Automated by TieBreaker cost engine',
        'Customer history indicates legitimacy',
        'Velocity pattern suspicious — manual review',
        'Merchant category typically low risk',
        'High LTV customer — preserve relationship'
    ]
    
    logs = []
    base = datetime(2024, 1, 15, 10, 0, 0)
    for i in range(limit):
        ts = base + timedelta(minutes=i * 7)
        logs.append({
            'timestamp': ts.isoformat(),
            'user': random.choice(users),
            'action': random.choice(actions),
            'entity_type': 'transaction',
            'entity_id': f'TXN{i:07d}',
            'details': random.choice(reasons),
            'model_version': '1.0',
            'config_version': '1.0'
        })
    
    return {'logs': logs, 'total': limit}

@router.get('/audit/decisions')
def get_decisions():
    return {'decisions': []}
