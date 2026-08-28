import pytest
from app.models import Override, AuditLog


class TestOverrideAPI:
    def test_override_transaction(self, client, db_session):
        response = client.post(
            "/api/transactions/TXN-TEST-001/override",
            params={
                "action": "BLOCK",
                "reason": "Suspicious velocity pattern",
                "analyst_id": "analyst_001",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["overridden_action"] == "BLOCK"
        assert data["transaction_id"] == "TXN-TEST-001"

    def test_override_invalid_action(self, client):
        response = client.post(
            "/api/transactions/TXN-TEST-002/override",
            params={
                "action": "INVALID",
                "reason": "Test",
                "analyst_id": "analyst_001",
            },
        )
        assert response.status_code == 400

    def test_override_creates_audit_log(self, client, db_session):
        client.post(
            "/api/transactions/TXN-TEST-003/override",
            params={
                "action": "ALLOW",
                "reason": "Customer verified",
                "analyst_id": "analyst_002",
            },
        )
        audit = db_session.query(AuditLog).filter(AuditLog.entity_id == "TXN-TEST-003").first()
        assert audit is not None
        assert audit.action == "OVERRIDE"
        assert "ALLOW" in audit.details

    def test_override_persists_in_db(self, client, db_session):
        client.post(
            "/api/transactions/TXN-TEST-004/override",
            params={
                "action": "REVIEW",
                "reason": "High value transaction",
                "analyst_id": "analyst_003",
            },
        )
        override = db_session.query(Override).filter(Override.transaction_id == "TXN-TEST-004").first()
        assert override is not None
        assert override.overridden_action == "REVIEW"