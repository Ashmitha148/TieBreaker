from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings

client = TestClient(app)


def test_create_order_unconfigured_returns_503(monkeypatch):
    """When Razorpay credentials are not configured, order creation returns HTTP 503."""
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "")

    response = client.post(
        "/api/orders",
        json={"amount": 50000, "currency": "INR", "receipt": "test_rcpt_001"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_create_order_invalid_amount_returns_422():
    """Negative or zero amounts are rejected with HTTP 422 Unprocessable Entity."""
    # Zero amount
    res0 = client.post("/api/orders", json={"amount": 0, "currency": "INR"})
    assert res0.status_code == 422

    # Negative amount
    res_neg = client.post("/api/orders", json={"amount": -500, "currency": "INR"})
    assert res_neg.status_code == 422


def test_create_order_missing_amount_returns_422():
    """Missing required amount field is rejected with HTTP 422."""
    res = client.post("/api/orders", json={"currency": "INR"})
    assert res.status_code == 422


def test_create_order_success_with_mocked_razorpay_client(monkeypatch):
    """When Razorpay credentials are set, order is created via Razorpay client and saved to DB."""
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_validkey123")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "secret123456789")

    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_test_999888",
        "entity": "order",
        "amount": 50000,
        "amount_paid": 0,
        "amount_due": 50000,
        "currency": "INR",
        "receipt": "test_rcpt_002",
        "status": "created",
        "attempts": 0,
    }

    with patch("razorpay.Client", return_value=mock_client):
        response = client.post(
            "/api/orders",
            json={"amount": 50000, "currency": "INR", "receipt": "test_rcpt_002"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["razorpay_order_id"] == "order_test_999888"
        assert data["amount"] == 50000
        assert data["currency"] == "INR"
        assert data["status"] == "created"
        assert data["key_id"] == "rzp_test_validkey123"


def test_list_orders():
    """Verify GET /api/orders returns list of saved orders."""
    response = client.get("/api/orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)