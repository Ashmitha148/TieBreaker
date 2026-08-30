from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_check_returns_200():
    """GET /health always returns HTTP 200 with a real status.

    FIXED: this used to require the literal {"status": "healthy"}, but the
    real health check reports "ok" or "degraded" (with reasons) depending on
    whether Redis/ML artifacts are actually available -- "healthy" is never
    a value the endpoint returns. A test environment with no Redis running
    correctly reports "degraded", which is honest, not a bug.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "ml" in data
    assert "velocity_engine" in data
    assert "degraded_reasons" in data


def test_root_returns_200():
    """GET / returns HTTP 200 and basic project metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("project") == "TieBreaker"
    assert data.get("status") == "ready"
    assert "phase" in data