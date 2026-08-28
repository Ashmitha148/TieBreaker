import pytest


class TestWebhookEndpoint:
    def test_webhook_list_empty(self, client):
        response = client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_webhook_accepted_in_test_mode(self, client):
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
        response = client.post(
            "/api/webhooks/razorpay",
            json=payload,
            headers={"x-razorpay-event-id": "evt_test_001"},
        )
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
        response = client.post(
            "/api/webhooks/razorpay",
            json=payload,
            headers={"x-razorpay-event-id": "evt_test_002"},
        )
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
        headers = {"x-razorpay-event-id": "evt_test_dup"}
        r1 = client.post("/api/webhooks/razorpay", json=payload, headers=headers)
        assert r1.status_code == 200
        r2 = client.post("/api/webhooks/razorpay", json=payload, headers=headers)
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
        response = client.post(
            "/api/webhooks/razorpay",
            json=payload,
            headers={"x-razorpay-event-id": "evt_test_004"},
        )
        assert response.status_code == 200

    def test_webhook_list_has_events(self, client):
        response = client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) > 0
