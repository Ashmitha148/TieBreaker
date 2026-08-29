"""API key authentication for TieBreaker mutating / scoring endpoints.

Webhook delivery is intentionally not covered here — Razorpay authenticates
those requests with HMAC-SHA256, not X-API-Key.
"""

from fastapi import Header, HTTPException, status

from .config import settings


async def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    configured = (settings.TIEBREAKER_API_KEY or "").strip()
    is_production = (settings.ENVIRONMENT or "").lower() == "production"

    if not configured:
        if is_production:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TIEBREAKER_API_KEY is not configured. Refusing to serve unauthenticated traffic.",
            )
        # Local/dev/test: no key configured, so this dependency is a no-op.
        return ""

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
        )
    if x_api_key != configured:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return x_api_key
