"""
ML pipeline tests (ticket item 5).

A couple of these deliberately force the heuristic fallback path
(by clearing the loaded model on the singleton ModelManager and restoring
it afterwards) rather than testing whichever trained artifact happens to be
on disk. The trained fraud/FP models are gradient-boosted trees fit on a
noisy synthetic generator; their pointwise behavior at two arbitrary input
points isn't guaranteed to be monotonic even when the underlying relationship
is real, so pinning a test to that would be flaky. The heuristic formulas are
linear and deterministic by construction, so they're the reliable place to
assert a directional relationship holds.
"""
import pytest

from app.ml.predictor import predict_transaction
from app.ml.models import get_model_manager


BASE_RECORD = {
    "amount": 50000,
    "velocity_1h": 1,
    "velocity_24h": 5,
    "device_change_flag": 0,
    "geo_mismatch_flag": 0,
    "is_cross_border": 0,
    "hour_of_day": 14,
    "customer_tenure_days": 365,
    "customer_tx_count_30d": 20,
    "customer_refund_rate": 0.05,
    "merchant_category": "Retail",
}


@pytest.fixture
def clean_models():
    """Temporarily clear the singleton's loaded models to force the
    heuristic fallback path, then restore whatever was loaded before."""
    mgr = get_model_manager()
    saved = (mgr.fraud_model, mgr.fp_model, mgr.review_model)
    mgr.fraud_model = None
    mgr.fp_model = None
    mgr.review_model = None
    yield mgr
    mgr.fraud_model, mgr.fp_model, mgr.review_model = saved


class TestPredictTransaction:
    def test_returns_probabilities_in_unit_range(self):
        for record in [
            BASE_RECORD,
            dict(BASE_RECORD, amount=2_000_000, velocity_1h=20, geo_mismatch_flag=1),
            dict(BASE_RECORD, amount=100, customer_tenure_days=1),
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

        # Cross-check against the heuristic formula directly, to confirm
        # this actually exercised the fallback path and not a fluke.
        expected_fraud = mgr.predict_fraud_prob(BASE_RECORD)
        expected_fp = mgr.predict_fp_prob(BASE_RECORD)
        assert result["fraud_probability"] == expected_fraud
        assert result["fp_probability"] == expected_fp

    def test_fraud_probability_increases_with_velocity_1h(self, clean_models):
        low = predict_transaction(dict(BASE_RECORD, velocity_1h=0))
        high = predict_transaction(dict(BASE_RECORD, velocity_1h=10))
        assert high["fraud_probability"] > low["fraud_probability"]

    def test_fp_probability_decreases_with_customer_tenure(self, clean_models):
        new_customer = predict_transaction(dict(BASE_RECORD, customer_tenure_days=5))
        long_tenure = predict_transaction(dict(BASE_RECORD, customer_tenure_days=900))
        assert new_customer["fp_probability"] > long_tenure["fp_probability"]

    def test_shap_drivers_returns_three_items_with_valid_directions(self):
        result = predict_transaction(BASE_RECORD)
        drivers = result["shap_drivers"]
        assert len(drivers) == 3
        for driver in drivers:
            assert "feature" in driver
            assert driver["direction"] in ("increases", "decreases")
