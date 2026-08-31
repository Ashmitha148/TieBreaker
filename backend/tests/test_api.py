import pytest

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert "version" in data

def test_create_order_without_razorpay(client):
    response = client.post("/api/create-order", json={"amount": 50000})
    # Should return 503 if Razorpay not configured, or 201 if configured
    assert response.status_code in [201, 503]

def test_transaction_analysis(client):
    response = client.get("/api/transactions/TXN-TEST-001")
    assert response.status_code == 200
    data = response.json()
    assert "fraud_probability" in data
    assert "recommended_action" in data
    assert data["transaction_id"] == "TXN-TEST-001"

def test_config_endpoint(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "current" in data
