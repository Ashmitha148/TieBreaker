import logging
import threading
from collections import deque
from typing import Dict, Optional

import redis

from ..config import settings

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'FRAUD_LOSS_MULTIPLIER': 2.5,
    'FRICTION_COST_RATE': 0.05,
    'RESIDUAL_FRAUD_POST_3DS': 0.30,
    'ANALYST_HOUR_COST': 100.0,
    'DELAY_RISK_RATE': 0.15,
    'TARGET_REVIEW_RATE': 0.15,
    'INITIAL_REVIEW_RATE_PRIOR': 0.90,
    'PRIOR_WEIGHT': 50,
    'QUEUE_WINDOW_SIZE': 200,
    'ESCALATION_RATE': 12.0,
    'MAX_QUEUE_FACTOR': 5.0,
    'CUSTOMER_FRICTION_RATE': 0.02,
}


class _ReviewQueueTracker:
    """Redis-backed review queue tracker with in-memory fallback."""

    def __init__(self):
        self._redis = None
        self._fallback_window = deque(maxlen=DEFAULT_CONFIG['QUEUE_WINDOW_SIZE'])
        self._fallback_lock = threading.Lock()
        try:
            self._redis = redis.Redis.from_url(
                getattr(settings, "REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
                socket_connect_timeout=2,
            )
            self._redis.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable for review queue tracker: {e}")
            self._redis = None

    def reset(self, maxlen: Optional[int] = None):
        if self._redis:
            self._redis.delete("tiebreaker:review_queue")
        with self._fallback_lock:
            self._fallback_window = deque(
                maxlen=maxlen or DEFAULT_CONFIG['QUEUE_WINDOW_SIZE']
            )

    def record(self, was_review: bool):
        if self._redis:
            self._redis.lpush("tiebreaker:review_queue", 1 if was_review else 0)
            self._redis.ltrim(
                "tiebreaker:review_queue",
                0,
                DEFAULT_CONFIG['QUEUE_WINDOW_SIZE'] - 1,
            )
        else:
            with self._fallback_lock:
                self._fallback_window.append(1 if was_review else 0)

    def estimated_review_rate(self, prior: float, prior_weight: float) -> float:
        if self._redis:
            window = self._redis.lrange("tiebreaker:review_queue", 0, -1)
            n = len(window)
            observed_sum = sum(int(x) for x in window)
        else:
            with self._fallback_lock:
                n = len(self._fallback_window)
                observed_sum = sum(self._fallback_window)
        return (prior * prior_weight + observed_sum) / (prior_weight + n)

    def depth(self) -> int:
        if self._redis:
            return self._redis.llen("tiebreaker:review_queue")
        with self._fallback_lock:
            return len(self._fallback_window)


_queue_tracker = _ReviewQueueTracker()


def reset_queue_tracker(maxlen: Optional[int] = None):
    _queue_tracker.reset(maxlen)


def get_queue_state(config: dict = None) -> Dict:
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    rate = _queue_tracker.estimated_review_rate(
        cfg['INITIAL_REVIEW_RATE_PRIOR'], cfg['PRIOR_WEIGHT']
    )
    factor = (
        min(rate / cfg['TARGET_REVIEW_RATE'], cfg['MAX_QUEUE_FACTOR'])
        if cfg['TARGET_REVIEW_RATE']
        else 1.0
    )
    return {
        'estimated_review_rate': round(rate, 4),
        'target_review_rate': cfg['TARGET_REVIEW_RATE'],
        'queue_depth_factor': round(factor, 3),
        'decisions_tracked': _queue_tracker.depth(),
    }


def calculate_action_losses(
    fraud_prob: float,
    fp_prob: float,
    amount: float,
    ltv: float,
    config: dict = None,
    track: bool = True,
) -> Dict:
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    review_rate_estimate = _queue_tracker.estimated_review_rate(
        cfg['INITIAL_REVIEW_RATE_PRIOR'], cfg['PRIOR_WEIGHT']
    )
    queue_depth_factor = (
        min(review_rate_estimate / cfg['TARGET_REVIEW_RATE'], cfg['MAX_QUEUE_FACTOR'])
        if cfg['TARGET_REVIEW_RATE']
        else 1.0
    )

    over_capacity = max(0.0, queue_depth_factor - 1.0)
    effective_analyst_cost = cfg['ANALYST_HOUR_COST'] * (
        1 + cfg['ESCALATION_RATE'] * over_capacity
    )
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
        'BLOCK': round(block_loss, 2),
    }

    recommended = min(losses, key=losses.get)
    if recommended == 'REVIEW':
        reason = (
            f'REVIEW costs ₹{losses["REVIEW"]:,.0f} (queue at {review_rate_estimate:.0%} of capacity, '
            f'target {cfg["TARGET_REVIEW_RATE"]:.0%}), lower than the alternatives'
        )
    elif recommended == 'BLOCK':
        reason = (
            f'BLOCK minimizes loss at ₹{losses["BLOCK"]:,.0f} — fraud probability '
            f'({fraud_prob:.0%}) and transaction value make allowing too risky'
        )
    elif recommended == 'VERIFY':
        reason = (
            f'VERIFY at ₹{losses["VERIFY"]:,.0f} balances fraud reduction with customer experience'
        )
    else:
        reason = (
            f'ALLOW is lowest cost at ₹{losses["ALLOW"]:,.0f} — fraud risk is manageable'
        )

    sorted_losses = sorted(losses.items(), key=lambda x: x[1])
    confidence_gap = (
        sorted_losses[1][1] - sorted_losses[0][1] if len(sorted_losses) > 1 else 0
    )

    if track:
        _queue_tracker.record(recommended == 'REVIEW')

    return {
        'losses': losses,
        'recommended_action': recommended,
        'confidence_gap': round(confidence_gap, 2),
        'primary_reason': reason,
        'secondary_reason': (
            f'Queue depth factor {queue_depth_factor:.2f}x target — '
            'analyst cost and SLA risk scale with it'
        ),
        'is_counterintuitive': fraud_prob > 0.65 and recommended != 'BLOCK',
        'queue_state': {
            'estimated_review_rate': round(review_rate_estimate, 4),
            'queue_depth_factor': round(queue_depth_factor, 3),
        },
    }


def threshold_baseline_decision(fraud_prob: float) -> str:
    if fraud_prob > 0.7:
        return 'BLOCK'
    elif fraud_prob > 0.4:
        return 'REVIEW'
    elif fraud_prob > 0.2:
        return 'VERIFY'
    return 'ALLOW'