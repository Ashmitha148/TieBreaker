from collections import deque
from typing import Dict, Optional
import threading

DEFAULT_CONFIG = {
    'FRAUD_LOSS_MULTIPLIER': 2.5,
    'FRICTION_COST_RATE': 0.05,
    'RESIDUAL_FRAUD_POST_3DS': 0.30,
    'ANALYST_HOUR_COST': 100.0,
    'DELAY_RISK_RATE': 0.15,

    # --- Queue capacity / analyst bandwidth simulation ---
    # Analyst review capacity is scarce. We target at most TARGET_REVIEW_RATE
    # of traffic going to REVIEW. Since we don't know the true current load
    # the very first time this runs, we start from a conservative prior that
    # matches the previously-observed behavior (this system used to route
    # almost everything to REVIEW). As real decisions are recorded, the
    # estimate blends toward the actual observed rate.
    'TARGET_REVIEW_RATE': 0.15,
    'INITIAL_REVIEW_RATE_PRIOR': 0.90,
    'PRIOR_WEIGHT': 50,          # pseudo-observations backing the prior
    'QUEUE_WINDOW_SIZE': 200,    # rolling window of recent decisions
    'ESCALATION_RATE': 12.0,     # how aggressively analyst cost rises when over capacity
    'MAX_QUEUE_FACTOR': 5.0,     # cap on how far over target we let the estimate scale costs

    # Customer churn friction for actions that impose friction on the customer
    'CUSTOMER_FRICTION_RATE': 0.02,
}


class _ReviewQueueTracker:
    """Tracks a rolling estimate of what fraction of decisions are routed to
    REVIEW, so the cost model can simulate scarce analyst bandwidth. Thread
    safe because FastAPI can serve requests from a small thread pool.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._maxlen = DEFAULT_CONFIG['QUEUE_WINDOW_SIZE']
        self._window = deque(maxlen=self._maxlen)

    def reset(self, maxlen: Optional[int] = None):
        with self._lock:
            self._maxlen = maxlen or DEFAULT_CONFIG['QUEUE_WINDOW_SIZE']
            self._window = deque(maxlen=self._maxlen)

    def record(self, was_review: bool):
        with self._lock:
            if self._window.maxlen != self._maxlen:
                self._window = deque(self._window, maxlen=self._maxlen)
            self._window.append(1 if was_review else 0)

    def estimated_review_rate(self, prior: float, prior_weight: float) -> float:
        with self._lock:
            n = len(self._window)
            observed_sum = sum(self._window)
        # Bayesian-ish blend: prior_weight pseudo-observations at `prior`,
        # smoothly overtaken by real traffic as it accumulates.
        return (prior * prior_weight + observed_sum) / (prior_weight + n)

    def depth(self) -> int:
        with self._lock:
            return len(self._window)


_queue_tracker = _ReviewQueueTracker()


def reset_queue_tracker(maxlen: Optional[int] = None):
    """Reset the in-process queue-depth tracker back to its initial prior.
    Intended for tests and ops tooling — normal request handling should NOT
    call this, since state is meant to persist across requests.
    """
    _queue_tracker.reset(maxlen)


def get_queue_state(config: dict = None) -> Dict:
    """Expose the current queue-pressure estimate, e.g. for a status endpoint."""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    rate = _queue_tracker.estimated_review_rate(cfg['INITIAL_REVIEW_RATE_PRIOR'], cfg['PRIOR_WEIGHT'])
    factor = min(rate / cfg['TARGET_REVIEW_RATE'], cfg['MAX_QUEUE_FACTOR']) if cfg['TARGET_REVIEW_RATE'] else 1.0
    return {
        'estimated_review_rate': round(rate, 4),
        'target_review_rate': cfg['TARGET_REVIEW_RATE'],
        'queue_depth_factor': round(factor, 3),
        'decisions_tracked': _queue_tracker.depth(),
    }


def calculate_action_losses(fraud_prob: float, fp_prob: float, amount: float, ltv: float,
                             config: dict = None, track: bool = True) -> Dict:
    # Merge with defaults rather than fully replacing, so callers (and older
    # configs) don't need to know about every queue-capacity knob.
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    review_rate_estimate = _queue_tracker.estimated_review_rate(
        cfg['INITIAL_REVIEW_RATE_PRIOR'], cfg['PRIOR_WEIGHT']
    )
    queue_depth_factor = min(
        review_rate_estimate / cfg['TARGET_REVIEW_RATE'], cfg['MAX_QUEUE_FACTOR']
    ) if cfg['TARGET_REVIEW_RATE'] else 1.0

    # Effective analyst cost rises once the queue runs over its capacity
    # target, standing in for the fact that scarce analysts get more
    # expensive to route work to (overtime, escalation, backlog risk).
    over_capacity = max(0.0, queue_depth_factor - 1.0)
    effective_analyst_cost = cfg['ANALYST_HOUR_COST'] * (1 + cfg['ESCALATION_RATE'] * over_capacity)

    # SLA breach risk: the longer a case sits in a congested queue, the more
    # likely a risky transaction breaches its resolution SLA before it's
    # actually reviewed.
    delay_risk = cfg['DELAY_RISK_RATE'] * queue_depth_factor * fraud_prob

    friction_cost = ltv * cfg['CUSTOMER_FRICTION_RATE']

    allow_loss = fraud_prob * amount * cfg['FRAUD_LOSS_MULTIPLIER']
    block_loss = fp_prob * (amount + ltv) + friction_cost
    verify_loss = (
        cfg['FRICTION_COST_RATE'] * amount
        + fraud_prob * cfg['RESIDUAL_FRAUD_POST_3DS'] * amount * cfg['FRAUD_LOSS_MULTIPLIER']
        + friction_cost
    )
    review_loss = effective_analyst_cost + delay_risk * amount

    losses = {
        'ALLOW': round(allow_loss, 2),
        'VERIFY': round(verify_loss, 2),
        'REVIEW': round(review_loss, 2),
        'BLOCK': round(block_loss, 2)
    }

    # No hardcoded overrides — the cost model must stand on its own. High
    # fraud_prob naturally drives ALLOW/VERIFY loss up (via the fraud-loss
    # terms above) relative to REVIEW/BLOCK, so it doesn't need a special case.
    recommended = min(losses, key=losses.get)
    if recommended == 'REVIEW':
        reason = (
            f'REVIEW costs ₹{losses["REVIEW"]:,.0f} (queue at {review_rate_estimate:.0%} of capacity, '
            f'target {cfg["TARGET_REVIEW_RATE"]:.0%}), lower than the alternatives'
        )
    elif recommended == 'BLOCK':
        reason = f'BLOCK minimizes loss at ₹{losses["BLOCK"]:,.0f} — fraud probability ({fraud_prob:.0%}) and transaction value make allowing too risky'
    elif recommended == 'VERIFY':
        reason = f'VERIFY at ₹{losses["VERIFY"]:,.0f} balances fraud reduction with customer experience'
    else:
        reason = f'ALLOW is lowest cost at ₹{losses["ALLOW"]:,.0f} — fraud risk is manageable'

    sorted_losses = sorted(losses.items(), key=lambda x: x[1])
    confidence_gap = sorted_losses[1][1] - sorted_losses[0][1] if len(sorted_losses) > 1 else 0

    if track:
        _queue_tracker.record(recommended == 'REVIEW')

    return {
        'losses': losses,
        'recommended_action': recommended,
        'confidence_gap': round(confidence_gap, 2),
        'primary_reason': reason,
        'secondary_reason': f'Queue depth factor {queue_depth_factor:.2f}x target — analyst cost and SLA risk scale with it',
        'is_counterintuitive': fraud_prob > 0.65 and recommended != 'BLOCK',
        'queue_state': {
            'estimated_review_rate': round(review_rate_estimate, 4),
            'queue_depth_factor': round(queue_depth_factor, 3),
        },
    }


def threshold_baseline_decision(fraud_prob: float) -> str:
    if fraud_prob > 0.7: return 'BLOCK'
    elif fraud_prob > 0.4: return 'REVIEW'
    elif fraud_prob > 0.2: return 'VERIFY'
    return 'ALLOW'