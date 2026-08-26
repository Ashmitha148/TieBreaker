from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_check_returns_200():
    """Verify GET /health returns HTTP 200 and healthy status independent of DB."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_returns_200():
    """Verify GET / returns HTTP 200 and basic metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("project") == "TieBreaker"
    assert data.get("phase") in ["Phase 0", "Phase 1"]
    assert data.get("status") == "ready"