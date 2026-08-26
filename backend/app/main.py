from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .routes import orders, webhooks, payments, config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TieBreaker - Payment Routing & Strike Decision Engine (Phase 1)",
    version="0.2.0",
    openapi_url="/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS configuration - supports exact deployed frontend URL plus localhost
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routers
app.include_router(orders.router)
app.include_router(webhooks.router)
app.include_router(payments.router)
app.include_router(config.router)


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    response_description="Service health status",
)
def health_check():
    """
    Independent health check endpoint.
    Returns HTTP 200 whenever the FastAPI backend is running.
    Does not require database connectivity.
    """
    return {"status": "healthy"}


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root endpoint",
)
def root():
    return {
        "project": settings.PROJECT_NAME,
        "phase": "Phase 1",
        "status": "ready",
        "razorpay_configured": settings.is_razorpay_configured,
        "environment": settings.ENVIRONMENT,
    }