from fastapi import APIRouter

router = APIRouter()

@router.get('/insights')
def get_insights():
    return {
        'before': {
            'false_decline_rate': 2.8,
            'fraud_capture_rate': 82.0,
            'avg_review_time': 8.5,
            'customer_friction_score': 6.2,
            'monthly_loss': 1250000
        },
        'after': {
            'false_decline_rate': 1.2,
            'fraud_capture_rate': 84.5,
            'avg_review_time': 4.2,
            'customer_friction_score': 3.8,
            'monthly_loss': 980000
        },
        'segments': [
            {'segment': 'Retail | New | Low', 'override_count': 12, 'accuracy': 0.75, 'ltv_adjustment': 0.95},
            {'segment': 'SaaS | Regular | Mid', 'override_count': 8, 'accuracy': 0.88, 'ltv_adjustment': 1.02},
            {'segment': 'B2B | VIP | High', 'override_count': 3, 'accuracy': 0.92, 'ltv_adjustment': 1.08},
            {'segment': 'Food | New | Low', 'override_count': 15, 'accuracy': 0.68, 'ltv_adjustment': 0.88}
        ],
        'net_improvement': {
            'loss_reduction_pct': 21.6,
            'friction_reduction_pct': 38.7,
            'review_efficiency_pct': 50.6
        }
    }
