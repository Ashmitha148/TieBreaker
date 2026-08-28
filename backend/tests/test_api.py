import pytest

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_create_order_without_razorpay(client):
    response = client.post("/api/v1/orders", json={"amount": 50000})
    # Should return 503 if Razorpay not configured, or 201 if configured
    assert response.status_code in [201, 503]

def test_transaction_analysis(client):
    response = client.get("/api/v1/transactions/TXN-TEST-001")
    assert response.status_code == 200
    data = response.json()
    assert "fraud_probability" in data
    assert "recommended_action" in data
    assert data["transaction_id"] == "TXN-TEST-001"

def test_velocity_score_endpoint(client):
    response = client.post(
        "/api/v1/velocity/score",
        params={
            "customer_id": "CUST-001",
            "amount": 50000,
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "composite_risk_score" in data
    assert "velocity" in data

def test_config_endpoint(client):
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert "current" in data