import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base, get_db
from app.main import app
from app.services.strike_selector import reset_queue_tracker
from app.config import settings

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


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
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