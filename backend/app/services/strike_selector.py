from typing import Dict

DEFAULT_CONFIG = {
    'FRAUD_LOSS_MULTIPLIER': 2.5,
    'FRICTION_COST_RATE': 0.05,
    'RESIDUAL_FRAUD_POST_3DS': 0.30,
    'ANALYST_HOUR_COST': 100.0,
    'DELAY_RISK_RATE': 0.15
}

def calculate_action_losses(fraud_prob: float, fp_prob: float, amount: float, ltv: float, config: dict = None) -> Dict:
    cfg = config or DEFAULT_CONFIG
    
    allow_loss = fraud_prob * amount * cfg['FRAUD_LOSS_MULTIPLIER']
    block_loss = fp_prob * (amount + ltv)
    verify_loss = cfg['FRICTION_COST_RATE'] * amount + fraud_prob * cfg['RESIDUAL_FRAUD_POST_3DS'] * amount * cfg['FRAUD_LOSS_MULTIPLIER']
    review_loss = cfg['ANALYST_HOUR_COST'] + fraud_prob * cfg['DELAY_RISK_RATE'] * amount * cfg['FRAUD_LOSS_MULTIPLIER']
    
    losses = {
        'ALLOW': round(allow_loss, 2),
        'VERIFY': round(verify_loss, 2),
        'REVIEW': round(review_loss, 2),
        'BLOCK': round(block_loss, 2)
    }
    
    if fraud_prob > 0.90:
        recommended = 'REVIEW'
        reason = 'Fraud probability exceeds 90% — mandatory human review required'
    else:
        recommended = min(losses, key=losses.get)
        if recommended == 'REVIEW':
            reason = f'REVIEW costs ₹{losses["REVIEW"]:,.0f}, lower than BLOCK (₹{losses["BLOCK"]:,.0f}) because customer LTV of ₹{ltv:,.0f} makes false-positive blocking expensive'
        elif recommended == 'BLOCK':
            reason = f'BLOCK minimizes loss at ₹{losses["BLOCK"]:,.0f} — fraud probability ({fraud_prob:.0%}) and transaction value make allowing too risky'
        elif recommended == 'VERIFY':
            reason = f'VERIFY at ₹{losses["VERIFY"]:,.0f} balances fraud reduction with customer experience'
        else:
            reason = f'ALLOW is lowest cost at ₹{losses["ALLOW"]:,.0f} — fraud risk is manageable'
    
    sorted_losses = sorted(losses.items(), key=lambda x: x[1])
    confidence_gap = sorted_losses[1][1] - sorted_losses[0][1] if len(sorted_losses) > 1 else 0
    
    return {
        'losses': losses,
        'recommended_action': recommended,
        'confidence_gap': round(confidence_gap, 2),
        'primary_reason': reason,
        'secondary_reason': 'Evaluated by deterministic cost engine with configurable parameters',
        'is_counterintuitive': fraud_prob > 0.65 and recommended != 'BLOCK'
    }

def threshold_baseline_decision(fraud_prob: float) -> str:
    if fraud_prob > 0.7: return 'BLOCK'
    elif fraud_prob > 0.4: return 'REVIEW'
    elif fraud_prob > 0.2: return 'VERIFY'
    return 'ALLOW'
