from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from .database import engine, Base, ensure_sqlite_decision_columns
from .routes import orders, payments, webhooks
from .routes import transactions, metrics, demo, queue, insights, audit, config as config_route
from .routes import cost_config, stream, whatif, learning
from .startup import ensure_models_trained
from .config import settings
from .ml.models import get_model_manager
from . import models as _models  # noqa: F401 — register tables on Base.metadata

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only auto-create tables in development (production should use Alembic migrations)
    if settings.ENVIRONMENT == "development":
        Base.metadata.create_all(bind=engine)
        ensure_sqlite_decision_columns()

    # Train models in background in dev; in production, validate artifacts exist
    if settings.ENVIRONMENT == "development":
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, ensure_models_trained)
    else:
        # Production: fail fast if ML artifacts are missing
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
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

    # Determine real status
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