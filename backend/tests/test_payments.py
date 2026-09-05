import hashlib
import hmac

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import Order

client = TestClient(app)


def test_list_payments_returns_persisted_records():
    """Verify GET /api/payments lists transactions correctly."""
    response = client.get("/api/payments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_verify_checkout_payment_unconfigured_returns_503(monkeypatch):
    """When Razorpay is not configured, POST /api/payment/verify returns HTTP 503."""
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "")

    response = client.post(
        "/api/payment/verify",
        json={
            "razorpay_order_id": "order_unconf_001",
            "razorpay_payment_id": "pay_unconf_001",
            "razorpay_signature": "sig_unconf_001",
        },
    )
    assert response.status_code == 503


def test_verify_checkout_missing_fields_returns_422():
    """Missing fields in verification request returns HTTP 422."""
    res = client.post("/api/payment/verify", json={"razorpay_order_id": "order_only"})
    assert res.status_code == 422


def test_verify_checkout_payment_valid_signature(monkeypatch):
    """Client payment verification endpoint validates checkout signatures."""
    test_secret = "test_key_secret_999"
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_999")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", test_secret)

    order_id = "order_verify_test_001"
    payment_id = "pay_verify_test_001"
    signature = hmac.new(
        test_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    # Pre-create order
    db = SessionLocal()
    try:
        order = Order(razorpay_order_id=order_id, amount=50000, currency="INR", status="created")
        db.add(order)
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/payment/verify",
        json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    db = SessionLocal()
    try:
        updated_order = db.query(Order).filter(Order.razorpay_order_id == order_id).first()
        assert updated_order.status == "paid"
    finally:
        db.close()


def test_verify_checkout_payment_invalid_signature(monkeypatch):
    """Client payment verification rejects invalid signatures with HTTP 400."""
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_999")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test_key_secret_999")

    response = client.post(
        "/api/payment/verify",
        json={
            "razorpay_order_id": "order_bad_sig_001",
            "razorpay_payment_id": "pay_bad_sig_001",
            "razorpay_signature": "invalid_signature_hash",
        },
    )
    assert response.status_code == 400
    assert "Invalid payment signature" in response.json()["detail"]