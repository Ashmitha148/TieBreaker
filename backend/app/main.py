from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .database import engine, Base
from .routes import orders, payments, webhooks
from .routes import transactions, metrics, demo, queue, insights, audit, config as config_route
from .routes import cost_config, stream, whatif, learning
from .startup import ensure_models_trained
from .config import settings
from .rate_limit import limiter
from .ml.models import get_model_manager
from .middleware.correlation import CorrelationIdMiddleware
from . import models as _models  # noqa: F401 — register tables on Base.metadata

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # SQLite production guard
    if settings.ENVIRONMENT == "production" and "sqlite" in settings.DATABASE_URL.lower():
        raise RuntimeError("SQLite is not allowed in production")

    # Run Alembic migrations in all environments
    from alembic.config import Config
    from alembic import command
    from pathlib import Path
    alembic_ini = Path(__file__).parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    command.upgrade(alembic_cfg, "head")

    # Train models in background in dev; in production, validate artifacts exist
    if settings.ENVIRONMENT == "development":
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, ensure_models_trained)
    else:
        mgr = get_model_manager()
        fraud_loaded = mgr.fraud_model is not None
        fp_loaded = mgr.fp_model is not None

        if not fraud_loaded or not fp_loaded:
            logger.error(
                "CRITICAL: Required ML artifacts are missing in production."
            )
            raise RuntimeError(
                "Required ML artifacts are missing in production."
            )

        app.state.ml_degraded = False
        logger.info(
            f"Production ML check passed: fraud={fraud_loaded}, fp={fp_loaded}"
        )

    yield


app = FastAPI(
    title="TieBreaker API",
    description="Cost-aware payment fraud decision engine",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

_PRODUCTION_ALLOWED_ORIGINS = ["https://tie-breaker-pi.vercel.app"]

if settings.ENVIRONMENT == "production":
    configured = list(settings.BACKEND_CORS_ORIGINS)
    if configured != _PRODUCTION_ALLOWED_ORIGINS:
        logger.warning(
            "BACKEND_CORS_ORIGINS in production was %r — overriding to the "
            "locked-down production origin %r. Wildcards and localhost are "
            "never honored in production.",
            configured,
            _PRODUCTION_ALLOWED_ORIGINS,
        )
    cors_origins = _PRODUCTION_ALLOWED_ORIGINS
else:
    cors_origins = settings.BACKEND_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(queue.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(config_route.router, prefix="/api")
app.include_router(cost_config.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(whatif.router, prefix="/api")
app.include_router(learning.router, prefix="/api")


@app.get("/health", tags=["Health"])
def health_check():
    from .ml.predictor import get_model_health
    from .services.velocity_engine import get_velocity_engine

    ml_health = get_model_health()
    vel_engine = get_velocity_engine(fail_silent=True)

    status = "ok"
    degraded_reasons = []

    if not ml_health.get("fraud_model_loaded") and not ml_health.get("fp_model_loaded"):
        status = "degraded"
        degraded_reasons.append("ml_artifacts_missing")

    redis_ok = vel_engine.client is not None
    if not redis_ok:
        status = "degraded"
        degraded_reasons.append("redis_unavailable")

    if getattr(app.state, "ml_degraded", False):
        status = "degraded"
        degraded_reasons.append("production_ml_check_failed")

    return {
        "status": status,
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
        "ml": ml_health,
        "velocity_engine": {
            "redis_connected": redis_ok,
        },
        "degraded_reasons": degraded_reasons,
    }