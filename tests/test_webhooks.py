import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import Order, Payment, WebhookEvent

client = TestClient(app)
TEST_WEBHOOK_SECRET = "test_webhook_secret_key_12345"


def generate_signature(body_bytes: bytes, secret: str) -> str:
    """Computes HMAC-SHA256 signature for test payloads."""
    return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()


def test_webhook_missing_signature_returns_400(monkeypatch):
    """Webhooks without X-Razorpay-Signature header are rejected with HTTP 400."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    payload = {"event": "payment.captured", "id": "evt_test_001"}
    response = client.post("/api/webhooks/razorpay", json=payload)
    assert response.status_code == 400
    assert "Missing X-Razorpay-Signature" in response.json()["detail"]


def test_webhook_invalid_signature_returns_400(monkeypatch):
    """Webhooks with an invalid HMAC-SHA256 signature are rejected with HTTP 400."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    payload = json.dumps({"event": "payment.captured", "id": "evt_test_002"}).encode("utf-8")
    headers = {
        "X-Razorpay-Signature": "invalid_fake_signature_hex",
        "X-Razorpay-Event-Id": "evt_test_002",
        "Content-Type": "application/json",
    }
    response = client.post("/api/webhooks/razorpay", content=payload, headers=headers)
    assert response.status_code == 400
    assert "Invalid webhook signature" in response.json()["detail"]


def test_webhook_empty_body_returns_400(monkeypatch):
    """Webhooks with an empty body are rejected with HTTP 400."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    headers = {
        "X-Razorpay-Signature": "some_sig",
        "Content-Type": "application/json",
    }
    response = client.post("/api/webhooks/razorpay", content=b"", headers=headers)
    assert response.status_code == 400


def test_webhook_malformed_json_returns_400(monkeypatch):
    """Webhooks with malformed JSON body but valid signature format are rejected with HTTP 400."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    bad_bytes = b"not-a-json-payload-{"
    sig = generate_signature(bad_bytes, TEST_WEBHOOK_SECRET)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_malformed_001",
        "Content-Type": "application/json",
    }
    response = client.post("/api/webhooks/razorpay", content=bad_bytes, headers=headers)
    assert response.status_code == 400
    assert "Malformed JSON" in response.json()["detail"]


def test_webhook_missing_event_id_returns_400(monkeypatch):
    """Webhooks without an event ID in headers or body are rejected with HTTP 400."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    payload_dict = {"event": "payment.captured", "payload": {}}
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = generate_signature(payload_bytes, TEST_WEBHOOK_SECRET)
    headers = {
        "X-Razorpay-Signature": sig,
        "Content-Type": "application/json",
    }
    response = client.post("/api/webhooks/razorpay", content=payload_bytes, headers=headers)
    assert response.status_code == 400
    assert "Missing event ID" in response.json()["detail"]


def test_webhook_valid_signature_and_processing(monkeypatch):
    """Valid webhook is accepted with HTTP 200, persisted, and processed into DB."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    payload_dict = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_valid_001",
                    "order_id": "order_test_valid_001",
                    "amount": 50000,
                    "currency": "INR",
                    "status": "captured",
                    "method": "upi",
                    "vpa": "customer@okhdfcbank",
                    "email": "customer@example.com",
                    "contact": "+919999999999",
                }
            }
        },
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = generate_signature(payload_bytes, TEST_WEBHOOK_SECRET)
    event_id = "evt_test_valid_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/api/webhooks/razorpay", content=payload_bytes, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["event_id"] == event_id

    # Verify WebhookEvent and Payment in DB
    db = SessionLocal()
    try:
        event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
        assert event is not None
        assert event.event_type == "payment.captured"

        payment = db.query(Payment).filter(Payment.razorpay_payment_id == "pay_test_valid_001").first()
        assert payment is not None
        assert payment.amount == 50000
        assert payment.status == "captured"
        assert payment.method == "upi"
        assert payment.vpa == "customer@okhdfcbank"
    finally:
        db.close()


def test_webhook_payment_authorized_handling(monkeypatch):
    """Verifies payment.authorized event updates Payment status to authorized."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    payload_dict = {
        "event": "payment.authorized",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_auth_001",
                    "order_id": "order_test_auth_001",
                    "amount": 35000,
                    "currency": "INR",
                    "status": "authorized",
                    "method": "netbanking",
                    "bank": "HDFC",
                }
            }
        },
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = generate_signature(payload_bytes, TEST_WEBHOOK_SECRET)
    event_id = "evt_test_auth_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/api/webhooks/razorpay", content=payload_bytes, headers=headers)
    assert response.status_code == 200

    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.razorpay_payment_id == "pay_test_auth_001").first()
        assert payment is not None
        assert payment.status == "authorized"
        assert payment.bank == "HDFC"
        assert payment.method == "netbanking"
    finally:
        db.close()


def test_webhook_idempotency_duplicate_ignored(monkeypatch):
    """Submitting the same webhook event ID twice is ignored with HTTP 200 (idempotent)."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    payload_dict = {
        "event": "payment.authorized",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_idempotent_001",
                    "order_id": "order_test_idempotent_001",
                    "amount": 25000,
                    "currency": "INR",
                    "status": "authorized",
                    "method": "card",
                }
            }
        },
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = generate_signature(payload_bytes, TEST_WEBHOOK_SECRET)
    event_id = "evt_test_idempotent_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    # First delivery
    res1 = client.post("/api/webhooks/razorpay", content=payload_bytes, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "accepted"

    # Second (duplicate) delivery
    res2 = client.post("/api/webhooks/razorpay", content=payload_bytes, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "ignored"
    assert res2.json()["message"] == "Duplicate event ignored"


def test_webhook_payment_failed_persists_error_details(monkeypatch):
    """Failed payment webhooks persist error code, step, source, and description."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    payload_dict = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_failed_001",
                    "order_id": "order_test_failed_001",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment was declined by issuing bank",
                    "error_source": "issuing_bank",
                    "error_step": "payment_authentication",
                    "error_reason": "card_declined",
                }
            }
        },
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = generate_signature(payload_bytes, TEST_WEBHOOK_SECRET)
    event_id = "evt_test_failed_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/api/webhooks/razorpay", content=payload_bytes, headers=headers)
    assert response.status_code == 200

    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.razorpay_payment_id == "pay_test_failed_001").first()
        assert payment is not None
        assert payment.status == "failed"
        assert payment.error_code == "BAD_REQUEST_ERROR"
        assert payment.error_reason == "card_declined"
        assert payment.error_source == "issuing_bank"
    finally:
        db.close()


def test_webhook_event_order_tolerance(monkeypatch):
    """Payment arriving before order.paid event is handled gracefully."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    # 1. First event: payment.captured arrives
    pay_dict = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_async_order_001",
                    "order_id": "order_test_async_order_001",
                    "amount": 75000,
                    "currency": "INR",
                    "status": "captured",
                    "method": "upi",
                }
            }
        },
    }
    pay_bytes = json.dumps(pay_dict).encode("utf-8")
    client.post(
        "/api/webhooks/razorpay",
        content=pay_bytes,
        headers={
            "X-Razorpay-Signature": generate_signature(pay_bytes, TEST_WEBHOOK_SECRET),
            "X-Razorpay-Event-Id": "evt_order_tolerance_001",
            "Content-Type": "application/json",
        },
    )

    # 2. Second event: order.paid arrives later
    order_dict = {
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_test_async_order_001",
                    "amount": 75000,
                    "currency": "INR",
                    "status": "paid",
                    "receipt": "rcpt_async_001",
                }
            }
        },
    }
    order_bytes = json.dumps(order_dict).encode("utf-8")
    client.post(
        "/api/webhooks/razorpay",
        content=order_bytes,
        headers={
            "X-Razorpay-Signature": generate_signature(order_bytes, TEST_WEBHOOK_SECRET),
            "X-Razorpay-Event-Id": "evt_order_tolerance_002",
            "Content-Type": "application/json",
        },
    )

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.razorpay_order_id == "order_test_async_order_001").first()
        assert order is not None
        assert order.status == "paid"
        assert order.amount == 75000

        payment = db.query(Payment).filter(Payment.razorpay_payment_id == "pay_test_async_order_001").first()
        assert payment is not None
        assert payment.status == "captured"
    finally:
        db.close()