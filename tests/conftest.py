import pytest
from backend.app.database import engine, Base, SessionLocal


@pytest.fixture(autouse=True)
def clean_database():
    """Drops and re-creates all tables before each test to ensure test isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)