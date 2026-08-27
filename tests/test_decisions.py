from backend.app.main import app
from backend.app.services.strike_selector import calculate_action_losses, threshold_baseline_decision

def test_cost_engine_allow_low_risk(client):
    # Very low fraud, low amount, high LTV â†’ should favor ALLOW or VERIFY
    result = calculate_action_losses(0.01, 0.05, 5000, 100000)
    # Just verify ALLOW is cheaper than BLOCK
    assert result['losses']['ALLOW'] < result['losses']['BLOCK']
    # Recommended action should not be BLOCK for such low risk
    assert result['recommended_action'] != 'BLOCK'


def test_cost_engine_block_high_risk(client):
    result = calculate_action_losses(0.95, 0.05, 100000, 10000)
    # High fraud + low LTV â†’ should not ALLOW
    assert result['recommended_action'] in ['REVIEW', 'BLOCK']


def test_cost_engine_counterintuitive(client):
    result = calculate_action_losses(0.72, 0.85, 50000, 500000)
    assert result['is_counterintuitive'] is True
    assert result['recommended_action'] != 'BLOCK'


def test_cost_engine_savings_positive(client):
    result = calculate_action_losses(0.3, 0.4, 100000, 200000)
    baseline = threshold_baseline_decision(0.3)
    assert result['losses'][result['recommended_action']] <= result['losses'][baseline]


def test_threshold_baseline(client):
    assert threshold_baseline_decision(0.8) == 'BLOCK'
    assert threshold_baseline_decision(0.5) == 'REVIEW'
    assert threshold_baseline_decision(0.3) == 'VERIFY'
    assert threshold_baseline_decision(0.1) == 'ALLOW'


def test_api_transaction_detail(client):
    # Use a transaction ID that exists in the dataset
    response = client.get('/api/transactions/TXN-COUNTER-001')
    assert response.status_code == 200
    data = response.json()
    assert 'fraud_prob' in data
    assert 'decision' in data
    assert 'drivers' in data


def test_api_counterintuitive_demo(client):
    response = client.get('/api/demo/counterintuitive')
    assert response.status_code == 200
    data = response.json()
    assert data['decision']['is_counterintuitive'] is True

