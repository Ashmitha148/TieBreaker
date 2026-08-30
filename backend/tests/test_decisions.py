import pytest
from app.services.strike_selector import calculate_action_losses, threshold_baseline_decision, DEFAULT_CONFIG


class TestStrikeSelector:
    def test_calculate_allow_wins_low_risk(self):
        result = calculate_action_losses(
            fraud_prob=0.05,
            fp_prob=0.10,
            amount=50000,
            ltv=100000,
        )
        assert result["recommended_action"] == "ALLOW"
        assert "losses" in result
        assert all(k in result["losses"] for k in ["ALLOW", "VERIFY", "REVIEW", "BLOCK"])

    def test_counterintuitive_flag(self):
        result = calculate_action_losses(
            fraud_prob=0.72,
            fp_prob=0.35,
            amount=450000,
            ltv=1200000,
        )
        assert result["is_counterintuitive"] is True
        assert result["recommended_action"] != "BLOCK"

    def test_high_fraud_low_ltv_blocks(self):
        # The hardcoded "fraud_prob > 0.90 => REVIEW" override was removed
        # (ticket item 2): the cost model must decide on its own. With low
        # LTV there's little customer-relationship value to protect, so
        # BLOCK — not REVIEW — is the cost-optimal action here.
        result = calculate_action_losses(
            fraud_prob=0.95,
            fp_prob=0.05,
            amount=100000,
            ltv=50000,
        )
        assert result["recommended_action"] == "BLOCK"

    def test_threshold_baseline_decision(self):
        assert threshold_baseline_decision(0.05) == "ALLOW"
        assert threshold_baseline_decision(0.30) == "VERIFY"
        assert threshold_baseline_decision(0.55) == "REVIEW"
        assert threshold_baseline_decision(0.85) == "BLOCK"

    def test_losses_are_positive(self):
        result = calculate_action_losses(
            fraud_prob=0.5,
            fp_prob=0.2,
            amount=200000,
            ltv=300000,
        )
        for action, loss in result["losses"].items():
            assert loss >= 0

    def test_config_override(self):
        custom_config = {
            'FRAUD_LOSS_MULTIPLIER': 3.0,
            'FRICTION_COST_RATE': 0.10,
            'RESIDUAL_FRAUD_POST_3DS': 0.20,
            'ANALYST_HOUR_COST': 200.0,
            'DELAY_RISK_RATE': 0.20
        }
        result = calculate_action_losses(
            fraud_prob=0.4,
            fp_prob=0.2,
            amount=100000,
            ltv=200000,
            config=custom_config,
        )
        assert "recommended_action" in result

    def test_transaction_api_returns_decision(self, client):
        response = client.get("/api/transactions/TXN-COUNTER-001")
        assert response.status_code == 200
        data = response.json()
        assert data["transaction_id"] == "TXN-COUNTER-001"
        assert "recommended_action" in data
        assert "losses" in data
        assert "shap_drivers" in data
        assert isinstance(data["shap_drivers"], list)