import pytest


class TestInsightsAPI:
    def test_insights_returns_structure(self, client):
        response = client.get("/api/insights")
        assert response.status_code == 200
        data = response.json()
        assert "before" in data
        assert "after" in data
        assert "override_distribution" in data
        assert "segment_calibration" in data
        assert "learning_curve" in data

    def test_before_has_metrics(self, client):
        response = client.get("/api/insights")
        data = response.json()
        before = data["before"]
        assert "accuracy" in before
        assert "precision" in before
        assert "recall" in before

    def test_after_has_metrics(self, client):
        response = client.get("/api/insights")
        data = response.json()
        after = data["after"]
        assert "accuracy" in after
        assert "total_overrides" in after

    def test_learning_curve_is_list(self, client):
        response = client.get("/api/insights")
        data = response.json()
        assert isinstance(data["learning_curve"], list)
        assert len(data["learning_curve"]) > 0
        for point in data["learning_curve"]:
            assert "day" in point
            assert "accuracy" in point
