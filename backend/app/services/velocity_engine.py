"""
TieBreaker Velocity Engine — Redis-backed transaction velocity checks.
"""

import json
import time
import logging
from typing import Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class VelocityEngine:
    """Redis-backed velocity tracker for fraud signals."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0", fail_silent: bool = False):
        self.client = None
        self.fail_silent = fail_silent
        self._redis_url = redis_url

        if REDIS_AVAILABLE and redis_url:
            try:
                self.client = redis.from_url(redis_url, decode_responses=True)
                self.client.ping()
                logger.info("VelocityEngine: Redis connected")
            except Exception as e:
                self.client = None
                logger.error(f"VelocityEngine: Redis connection failed: {e}")
                if not fail_silent:
                    raise RuntimeError(f"Redis unavailable and fail_silent=False: {e}")
        else:
            logger.warning("VelocityEngine: redis-py not installed or no URL provided")

    def _key(self, prefix: str, identifier: str) -> str:
        return f"tiebreaker:{prefix}:{identifier}"

    def _tx_key(self, prefix: str, identifier: str) -> str:
        return f"tiebreaker:{prefix}:{identifier}:tx"

    def record_transaction(self, customer_id: str, amount: float, device_id: Optional[str] = None):
        """Log a transaction for velocity tracking with amount metadata."""
        if not self.client:
            if not self.fail_silent:
                raise RuntimeError("Redis unavailable — cannot record transaction velocity")
            logger.warning("VelocityEngine: skipping record_transaction (Redis down)")
            return

        now = time.time()
        tx_data = json.dumps({
            "timestamp": now,
            "amount": amount,
            "device_id": device_id,
        })

        pipe = self.client.pipeline()

        cust_key = self._tx_key("cust", customer_id)
        pipe.zadd(cust_key, {tx_data: now})
        pipe.zremrangebyscore(cust_key, 0, now - 86400)
        pipe.expire(cust_key, 86400)

        if device_id:
            dev_key = self._tx_key("dev", device_id)
            pipe.zadd(dev_key, {tx_data: now})
            pipe.zremrangebyscore(dev_key, 0, now - 86400)
            pipe.expire(dev_key, 86400)

        pipe.execute()

    def get_velocity(self, customer_id: str, device_id: Optional[str] = None) -> dict:
        """Get current velocity metrics for a customer/device."""
        if not self.client:
            if not self.fail_silent:
                raise RuntimeError("Redis unavailable — cannot read velocity")
            logger.warning("VelocityEngine: returning zeros (Redis down)")
            return {"velocity_1h": 0, "velocity_24h": 0, "device_tx_count_1h": 0, "degraded": True}

        now = time.time()
        cust_key = self._tx_key("cust", customer_id)

        tx_1h = self.client.zcount(cust_key, now - 3600, now) or 0
        tx_24h = self.client.zcount(cust_key, now - 86400, now) or 0

        result = {
            "velocity_1h": int(tx_1h),
            "velocity_24h": int(tx_24h),
            "device_tx_count_1h": 0,
            "degraded": False,
        }

        if device_id:
            dev_key = self._tx_key("dev", device_id)
            dev_1h = self.client.zcount(dev_key, now - 3600, now) or 0
            result["device_tx_count_1h"] = int(dev_1h)

        return result

    def get_customer_stats(self, customer_id: str) -> dict:
        """Aggregated stats for LTV estimation using REAL stored amounts."""
        if not self.client:
            if not self.fail_silent:
                raise RuntimeError("Redis unavailable — cannot read customer stats")
            logger.warning("VelocityEngine: returning zeros (Redis down)")
            return {"total_tx_30d": 0, "total_amount_30d": 0, "degraded": True}

        cust_key = self._tx_key("cust", customer_id)
        now = time.time()

        raw_txs = self.client.zrangebyscore(cust_key, now - 2592000, now) or []

        total_amount = 0.0
        for tx_json in raw_txs:
            try:
                tx = json.loads(tx_json)
                total_amount += float(tx.get("amount", 0))
            except (json.JSONDecodeError, ValueError):
                continue

        return {
            "total_tx_30d": len(raw_txs),
            "total_amount_30d": round(total_amount, 2),
            "degraded": False,
        }


# Singleton
_velocity_engine = None


def get_velocity_engine(redis_url: str = "redis://localhost:6379/0", fail_silent: bool = False):
    global _velocity_engine
    if _velocity_engine is None:
        _velocity_engine = VelocityEngine(redis_url, fail_silent=fail_silent)
    return _velocity_engine