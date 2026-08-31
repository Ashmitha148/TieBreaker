import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# CRITICAL: Override DATABASE_URL BEFORE importing database.py
import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base, get_db, SessionLocal
from app.main import app
from app.services.strike_selector import reset_queue_tracker
from app.config import settings
from app.models import Decision

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Monkey-patch SessionLocal so background tasks (webhooks) also use test DB
SessionLocal.configure(bind=engine)


# Fixed transaction_ids referenced directly by name in test_override.py,
# test_decisions.py, and test_api.py. Previously these resolved via a
# random-data-on-404 fallback in the GET endpoint; that fallback was removed
# as a security fix (ticket item 3), so the tests now need real rows.
SEEDED_TRANSACTION_IDS = ["TXN-TEST-001", "TXN-TEST-003", "TXN-TEST-004", "TXN-COUNTER-001"]


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        for txn_id in SEEDED_TRANSACTION_IDS:
            session.add(Decision(
                transaction_id=txn_id,
                fraud_prob=0.62,
                fp_prob=0.18,
                amount=180000,
                ltv=450000,
                merchant_category="Retail",
                recommended_action="REVIEW",
                baseline_action="REVIEW",
                savings_vs_baseline=0.0,
                model_version="test",
                config_version="test",
                is_counterintuitive=False,
                outcome=None,
            ))
        session.commit()
    finally:
        session.close()
    yield
    Base.metadata.drop_all(bind=engine)


TEST_WEBHOOK_SECRET = "test_webhook_secret_for_pytest_only"


@pytest.fixture(autouse=True)
def _configure_webhook_secret():
    # Webhook signature verification fails CLOSED when no secret is
    # configured (see app/routes/webhooks.py), so tests need a real secret
    # to sign against rather than relying on verification being skipped.
    original = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
    yield
    settings.RAZORPAY_WEBHOOK_SECRET = original


@pytest.fixture(autouse=True)
def _reset_review_queue_tracker():
    # The cost model's queue-capacity simulation keeps in-process rolling
    # state. Reset it before every test so results don't depend on test
    # execution order.
    reset_queue_tracker()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()