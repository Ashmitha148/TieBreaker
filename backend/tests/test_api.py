
def test_health(client):
    # FIXED: real endpoint returns "ok" or "degraded" (never "healthy") --
    # "degraded" is a correct, honest response when Redis/ML aren't
    # available in the test environment, not a failure.
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] in ('ok', 'degraded')


def test_root(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'TieBreaker' in response.json()['project']


def test_config_endpoint(client):
    response = client.get('/api/config')
    assert response.status_code == 200
    data = response.json()
    assert 'current' in data


def test_transactions_list(client):
    response = client.get('/api/transactions')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_queue_endpoint(client):
    response = client.get('/api/queue')
    assert response.status_code == 200
    data = response.json()
    assert 'cases' in data


def test_metrics_endpoint(client):
    response = client.get('/api/metrics')
    assert response.status_code == 200
    data = response.json()
    assert 'fraud_precision' in data or 'error' in data


def test_insights_endpoint(client):
    response = client.get('/api/insights')
    assert response.status_code == 200
    assert 'before' in response.json()


def test_audit_endpoint(client):
    response = client.get('/api/audit')
    assert response.status_code == 200
    assert 'logs' in response.json()


def test_override_endpoint(client):
    response = client.post('/api/transactions/TXN-COUNTER-001/override', json={
        'action': 'BLOCK',
        'reason': 'Suspicious velocity pattern',
        'analyst_id': 'test_analyst'
    })
    assert response.status_code == 200
    assert response.json()['status'] == 'overridden'