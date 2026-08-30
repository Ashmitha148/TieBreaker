import hashlib
import hmac
import json

import pytest

from tests.conftest import TEST_WEBHOOK_SECRET


def _sign(payload: dict) -> tuple[bytes, str]:
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(TEST_WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return body, signature


def _post_signed(client, payload: dict, event_id: str):
    body, signature = _sign(payload)
    return client.post(
        "/api/webhooks/razorpay",
        content=body,
        headers={
            "content-type": "application/json",
            "x-razorpay-event-id": event_id,
            "x-razorpay-signature": signature,
        },
    )


class TestWebhookEndpoint:
    def test_webhook_list_empty(self, client):
        response = client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_webhook_accepted_with_valid_signature(self, client):
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_001",
                        "amount": 50000,
                        "status": "captured",
                        "order_id": "order_test_001",
                    }
                }
            }
        }
        response = _post_signed(client, payload, "evt_test_001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "event_id" in data

    def test_webhook_payment_captured(self, client):
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_002",
                        "amount": 100000,
                        "status": "captured",
                        "method": "upi",
                    }
                }
            }
        }
        response = _post_signed(client, payload, "evt_test_002")
        assert response.status_code == 200
        assert response.json()["status"] == "received"

    def test_webhook_idempotency(self, client):
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_003",
                        "amount": 25000,
                        "status": "failed",
                    }
                }
            }
        }
        r1 = _post_signed(client, payload, "evt_test_dup")
        assert r1.status_code == 200
        r2 = _post_signed(client, payload, "evt_test_dup")
        assert r2.status_code == 200
        assert r2.json()["status"] == "already_processed"

    def test_webhook_order_paid_event(self, client):
        payload = {
            "event": "order.paid",
            "payload": {
                "order": {
                    "entity": {
                        "id": "order_test_004",
                        "amount": 75000,
                        "status": "paid",
                    }
                }
            }
        }
        response = _post_signed(client, payload, "evt_test_004")
        assert response.status_code == 200

    def test_webhook_list_has_events(self, client):
        response = client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) > 0

    # --- Fail-closed security behavior ---

    def test_webhook_rejects_missing_signature(self, client):
        payload = {"event": "payment.captured", "payload": {}}
        body = json.dumps(payload).encode("utf-8")
        response = client.post(
            "/api/webhooks/razorpay",
            content=body,
            headers={"content-type": "application/json", "x-razorpay-event-id": "evt_no_sig"},
        )
        assert response.status_code == 401

    def test_webhook_rejects_invalid_signature(self, client):
        payload = {"event": "payment.captured", "payload": {}}
        body = json.dumps(payload).encode("utf-8")
        response = client.post(
            "/api/webhooks/razorpay",
            content=body,
            headers={
                "content-type": "application/json",
                "x-razorpay-event-id": "evt_bad_sig",
                "x-razorpay-signature": "not_a_real_signature",
            },
        )
        assert response.status_code == 401

    def test_webhook_rejects_when_secret_not_configured(self, client, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
        monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "")
        payload = {"event": "payment.captured", "payload": {}}
        body = json.dumps(payload).encode("utf-8")
        response = client.post(
            "/api/webhooks/razorpay",
            content=body,
            headers={
                "content-type": "application/json",
                "x-razorpay-event-id": "evt_no_secret",
                "x-razorpay-signature": "irrelevant",
            },
        )
        assert response.status_code == 401