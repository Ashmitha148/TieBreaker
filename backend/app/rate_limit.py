"""Rate limiting for TieBreaker's scoring endpoints.

Keyed by API key (X-API-Key header) rather than IP, since the deployment
sits behind a shared load balancer/CDN where many legitimate clients can
share an IP, and the thing we actually want to protect is per-tenant
fairness. Falls back to remote address only when no API key is present
(e.g. local dev with TIEBREAKER_API_KEY unset).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _rate_limit_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_rate_limit_key)