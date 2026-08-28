import pytest


class TestQueueOracle:
    def test_queue_returns_data(self, client):
        response = client.get("/api/queue")
        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert "total" in data
        assert isinstance(data["cases"], list)
        assert len(data["cases"]) > 0

    def test_queue_cases_have_required_fields(self, client):
        response = client.get("/api/queue")
        data = response.json()
        for case in data["cases"]:
            assert "rank" in case
            assert "transaction_id" in case
            assert "amount" in case
            assert "fraud_probability" in case
            assert "recommended_action" in case
            assert "impact_score" in case

    def test_queue_respects_limit(self, client):
        response = client.get("/api/queue?limit=5")
        data = response.json()
        assert len(data["cases"]) <= 5

    def test_queue_min_fraud_filter(self, client):
        response = client.get("/api/queue?min_fraud_prob=0.5")
        data = response.json()
        for case in data["cases"]:
            assert case["fraud_probability"] >= 0.5

    def test_queue_sorted_by_impact(self, client):
        response = client.get("/api/queue")
        data = response.json()
        scores = [c["impact_score"] for c in data["cases"]]
        assert scores == sorted(scores, reverse=True)