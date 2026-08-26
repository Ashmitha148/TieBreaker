from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings

client = TestClient(app)


def test_public_config_endpoint_does_not_leak_secrets(monkeypatch):
    """GET /api/config exposes public key and environment without secrets."""
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_public_123")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "super_secret_key_never_leak")
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "webhook_secret_never_leak")

    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert data["is_configured"] is True
    assert data["is_test_mode"] is True
    assert data["razorpay_key_id"] == "rzp_test_public_123"

    # Crucial security check: Ensure secrets are not returned anywhere in response
    assert "super_secret_key_never_leak" not in str(data)
    assert "webhook_secret_never_leak" not in str(data)