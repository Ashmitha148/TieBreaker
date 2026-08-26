from fastapi import APIRouter
from ..config import settings
from ..schemas import ConfigResponse

router = APIRouter(prefix="/api/config", tags=["Config"])


@router.get("", response_model=ConfigResponse)
def get_public_config():
    """
    Returns public configuration for the frontend demo checkout.
    Never exposes secrets to the client.
    """
    return ConfigResponse(
        is_configured=settings.is_razorpay_configured,
        environment=settings.ENVIRONMENT,
        is_test_mode=True,
        razorpay_key_id=settings.RAZORPAY_KEY_ID if settings.is_razorpay_configured else None,
    )