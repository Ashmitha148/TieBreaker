import os
import sys

# Ensure both repo root and backend are in sys.path
_test_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.abspath(os.path.join(_test_dir, ".."))
if os.path.basename(_parent_dir) == "backend":
    _repo_root = os.path.abspath(os.path.join(_parent_dir, ".."))
    _backend_dir = _parent_dir
else:
    _repo_root = _parent_dir
    _backend_dir = os.path.abspath(os.path.join(_repo_root, "backend"))

for p in [_repo_root, _backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.config import settings

# Ensure app.* and backend.app.* share the same modules in sys.modules
import backend.app
sys.modules["app"] = backend.app
for sub in ["config", "database", "main", "models", "auth"]:
    if hasattr(backend.app, sub):
        sys.modules[f"app.{sub}"] = getattr(backend.app, sub)

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import backend.app.database as db_module
db_module.engine = engine
db_module.SessionLocal.configure(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once before any tests run, drop them after."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def ensure_webhook_secret(monkeypatch):
    """Provide a dummy webhook secret so webhook tests don't crash."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "whsec_test_dummy_secret_12345")
