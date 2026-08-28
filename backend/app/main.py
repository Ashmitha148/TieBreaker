from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import engine, Base
from .routes import orders, payments, webhooks
from .routes import transactions, metrics, demo, queue, insights, audit, config as config_route
from .startup import ensure_models_trained


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_models_trained()
    yield


app = FastAPI(
    title="TieBreaker API",
    description="Cost-aware payment fraud decision engine",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}
