from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


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
        "phase": "Phase 0",
        "status": "ready",
    }
