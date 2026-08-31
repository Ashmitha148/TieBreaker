"""
ML pipeline tests — Tier 1 real-data ready.

These tests validate the inference API and heuristic fallback paths.
They do NOT require trained artifacts (real data is not available in CI).
"""
import pytest

from app.ml.predictor import predict_transaction, get_model_health
from app.ml.models import get_model_manager


BASE_RECORD = {
    "TransactionAmt": 500.0,
    "amount": 500.0,
    "velocity_1h": 1,
    "velocity_24h": 5,
    "device_change_flag": 0,
    "geo_mismatch_flag": 0,
    "is_cross_border": 0,
    "hour_of_day": 14,
    "day_of_week": 3,
    "customer_tenure_days": 365,
    "customer_tx_count_30d": 20,
    "customer_refund_rate": 0.05,
    "merchant_category": "Retail",
    "C1": 1, "C2": 1, "C3": 0, "C4": 0, "C5": 0,
    "D1": 50, "D2": 30, "D3": 10,
    "V1": 1, "V2": 1, "V3": 0, "V4": 0, "V5": 0,
    "card1": 10000, "card2": 500, "card3": 150,
    "addr1": 300, "addr2": 80,
}

# Record that triggers multiple SHAP heuristic conditions
SHAP_RECORD = {
    "TransactionAmt": 150000.0,
    "amount": 150000.0,
    "velocity_1h": 10,
    "velocity_24h": 50,
    "device_change_flag": 1,
    "geo_mismatch_flag": 1,
    "is_cross_border": 1,
    "hour_of_day": 2,
    "day_of_week": 3,
    "customer_tenure_days": 10,
    "customer_tx_count_30d": 2,
    "customer_refund_rate": 0.0,
    "merchant_category": "Retail",
    "C1": 1, "C2": 1, "C3": 0, "C4": 0, "C5": 0,
    "D1": 5, "D2": 3, "D3": 1,
    "V1": 1, "V2": 1, "V3": 0, "V4": 0, "V5": 0,
    "card1": 10000, "card2": 500, "card3": 150,
    "addr1": 300, "addr2": 80,
}


@pytest.fixture
def clean_models():
    """Temporarily clear the singleton's loaded models to force the
    heuristic fallback path, then restore whatever was loaded before."""
    mgr = get_model_manager()
    saved = (mgr.fraud_model, mgr.fp_model)
    mgr.fraud_model = None
    mgr.fp_model = None
    yield mgr
    mgr.fraud_model, mgr.fp_model = saved


class TestPredictTransaction:
    def test_returns_probabilities_in_unit_range(self):
        for record in [
            BASE_RECORD,
            dict(BASE_RECORD, TransactionAmt=200000.0, velocity_1h=20, geo_mismatch_flag=1),
            dict(BASE_RECORD, TransactionAmt=10.0, customer_tenure_days=1),
        ]:
            result = predict_transaction(record)
            assert 0.0 <= result["fraud_probability"] <= 1.0
            assert 0.0 <= result["fp_probability"] <= 1.0

    def test_model_manager_falls_back_to_heuristic_when_artifacts_missing(self, clean_models):
        mgr = clean_models
        assert mgr.fraud_model is None
        assert mgr.fp_model is None

        result = predict_transaction(BASE_RECORD)
        assert 0.0 <= result["fraud_probability"] <= 1.0
        assert 0.0 <= result["fp_probability"] <= 1.0

        # Cross-check against the heuristic formula directly
        expected_fraud = mgr.predict_fraud_prob(BASE_RECORD)
        expected_fp = mgr.predict_fp_prob(BASE_RECORD)
        assert result["fraud_probability"] == expected_fraud
        assert result["fp_probability"] == expected_fp

    def test_fraud_probability_increases_with_amount(self, clean_models):
        low = predict_transaction(dict(BASE_RECORD, TransactionAmt=100.0))
        high = predict_transaction(dict(BASE_RECORD, TransactionAmt=200000.0))
        assert high["fraud_probability"] > low["fraud_probability"]

    def test_fp_probability_decreases_with_amount(self, clean_models):
        # FP heuristic: lower amount -> higher FP probability (inverted from old logic)
        low = predict_transaction(dict(BASE_RECORD, TransactionAmt=100.0))
        high = predict_transaction(dict(BASE_RECORD, TransactionAmt=200000.0))
        assert low["fp_probability"] > high["fp_probability"]

    def test_shap_drivers_returns_items_with_valid_directions(self):
        # Use SHAP_RECORD which triggers multiple heuristic conditions
        result = predict_transaction(SHAP_RECORD)
        drivers = result["shap_drivers"]
        assert len(drivers) >= 1
        for driver in drivers:
            assert "feature" in driver
            assert driver["direction"] in ("increases", "decreases")


class TestModelHealth:
    def test_health_returns_expected_keys(self):
        health = get_model_health()
        assert "fraud_model_loaded" in health
        assert "fp_model_loaded" in health
        assert "fraud_metrics" in health
        assert "fp_metrics" in health
        assert "review_model_loaded" not in health
