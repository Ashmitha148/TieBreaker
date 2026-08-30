from backend.app.config import settings
from backend.app.main import app


def test_decision_requires_api_key_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "TIEBREAKER_API_KEY", "test-secret")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    payload = {
        "transaction_id": "TXN-AUTH-001",
        "customer_id": "CUST-AUTH-001",
        "amount": 1500,
        "ltv": 8000,
    }
    denied = client.post("/api/transactions", json=payload)
    assert denied.status_code == 401

    ok = client.post("/api/transactions", json=payload, headers={"X-API-Key": "test-secret"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["transaction_id"] == "TXN-AUTH-001"
    assert "velocity_source" in body
    assert "model_version" in body


def test_what_if_single_override_does_not_require_both(client, monkeypatch):
    monkeypatch.setattr(settings, "TIEBREAKER_API_KEY", "test-secret")
    res = client.post(
        "/api/what-if",
        json={"amount": 2000, "ltv": 10000, "override_fraud_prob": 0.9},
        headers={"X-API-Key": "test-secret"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["model_inference"]["fraud_probability"] == 0.9
    assert data["model_inference"]["partial_override_note"] is not None


def test_webhook_does_not_require_api_key(client, monkeypatch):
    monkeypatch.setattr(settings, "TIEBREAKER_API_KEY", "test-secret")
    payload = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_auth_1", "amount": 100, "status": "captured"}}},
    }
    res = client.post(
        "/api/webhooks/razorpay",
        json=payload,
        headers={"x-razorpay-event-id": "evt_auth_1"},
    )
    assert res.status_code == 200
    assert res.json()["status"] in ("accepted", "ignored")


def test_production_refuses_unconfigured_api_key(client, monkeypatch):
    monkeypatch.setattr(settings, "TIEBREAKER_API_KEY", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res = client.post("/api/what-if", json={"amount": 100, "ltv": 100})
    assert res.status_code == 500