from fastapi import APIRouter

from .health import router as health_router
from .orders import router as orders_router
from .transactions import router as transactions_router
from .webhooks import router as webhooks_router
from .metrics import router as metrics_router
from .queue import router as queue_router
from .audit import router as audit_router
from .config import router as config_router
from .insights import router as insights_router
from .velocity import router as velocity_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health")
api_router.include_router(orders_router)
api_router.include_router(transactions_router)
api_router.include_router(webhooks_router)
api_router.include_router(metrics_router)
api_router.include_router(queue_router)
api_router.include_router(audit_router)
api_router.include_router(config_router)
api_router.include_router(insights_router)
api_router.include_router(velocity_router)
