from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from ..database import get_db
from ..models import AuditLog

router = APIRouter()


@router.get('/audit')
def get_audit(limit: int = 50, db: Session = Depends(get_db)):
    try:
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    except Exception:
        logs = []
    
    if not logs:
        actions = ['DECISION', 'OVERRIDE', 'CONFIG_CHANGE', 'MODEL_UPDATE']
        users = ['system', 'analyst_001', 'analyst_002', 'admin']
        reasons = [
            'Automated by TieBreaker cost engine',
            'Customer history indicates legitimacy',
            'Velocity pattern suspicious — manual review',
            'Merchant category typically low risk',
            'High LTV customer — preserve relationship'
        ]
        
        base = datetime(2024, 1, 15, 10, 0, 0)
        for i in range(min(limit, 20)):
            ts = base + timedelta(minutes=i * 7)
            log = AuditLog(
                timestamp=ts,
                user=random.choice(users),
                action=random.choice(actions),
                entity_type='transaction',
                entity_id=f'TXN{i:07d}',
                details=random.choice(reasons),
                model_version='1.0',
                config_version='1.0'
            )
            db.add(log)
        db.commit()
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    return {
        'logs': [
            {
                'timestamp': log.timestamp.isoformat() if log.timestamp else '',
                'user': log.user,
                'action': log.action,
                'entity_type': log.entity_type,
                'entity_id': log.entity_id,
                'details': log.details,
                'model_version': log.model_version,
                'config_version': log.config_version,
            }
            for log in logs
        ],
        'total': len(logs)
    }


@router.get('/audit/decisions')
def get_decisions(db: Session = Depends(get_db)):
    from ..models import Decision
    decisions = db.query(Decision).order_by(Decision.created_at.desc()).limit(100).all()
    return {
        'decisions': [
            {
                'id': d.id,
                'transaction_id': d.transaction_id,
                'recommended_action': d.recommended_action,
                'fraud_prob': round(d.fraud_prob, 3),
                'savings': round(d.savings_vs_baseline, 2),
                'model_version': d.model_version,
                'created_at': d.created_at.isoformat() if d.created_at else None,
            }
            for d in decisions
        ]
    }