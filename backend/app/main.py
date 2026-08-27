from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routes import orders, payments, webhooks
from .routes import transactions, metrics, demo, queue, insights, audit, config as config_route


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TieBreaker - Cost-Aware Risk Decision Engine",
    version="1.0.0",
    openapi_url="/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://tie-breaker-pi.vercel.app","http://localhost:5173","http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ALL routes under /api for consistency
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


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy"}


@app.get("/", status_code=status.HTTP_200_OK)
def root():
    return {
        "project": settings.PROJECT_NAME,
        "phase": "Phase 2 - ML + Decision Engine",
        "status": "ready",
        "razorpay_configured": settings.is_razorpay_configured,
        "environment": settings.ENVIRONMENT,
    }