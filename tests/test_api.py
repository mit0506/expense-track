import json


def test_api_expenses_returns_json(auth_client):
    resp = auth_client.get('/api/expenses')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'expenses' in data
    assert 'total' in data
    assert 'pages' in data


def test_api_expenses_pagination(auth_client):
    # Add some expenses
    for i in range(5):
        auth_client.post('/add_manual', data={
            'date': '2026-04-01',
            'merchant': f'Store {i}',
            'amount': '10',
            'category': 'Food',
            'payment_type': 'Cash',
        })

    resp = auth_client.get('/api/expenses?page=1&per_page=2')
    data = json.loads(resp.data)
    assert len(data['expenses']) == 2
    assert data['total'] == 5


def test_api_visualization_invalid_period(auth_client):
    resp = auth_client.get('/api/visualization/invalid')
    assert resp.status_code == 400


def test_api_visualization_monthly(auth_client):
    resp = auth_client.get('/api/visualization/monthly')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'pie' in data
    assert 'bar' in data
    assert 'total_amount' in data


def test_api_custom_visualization_missing_dates(auth_client):
    resp = auth_client.get('/api/visualization/custom')
    assert resp.status_code == 400


def test_api_custom_visualization_invalid_dates(auth_client):
    resp = auth_client.get('/api/visualization/custom?start=bad&end=bad')
    assert resp.status_code == 400


def test_api_custom_visualization_valid(auth_client):
    resp = auth_client.get('/api/visualization/custom?start=2026-01-01&end=2026-12-31')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'pie' in data


def test_chat_total(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'Chat Test',
        'amount': '200',
        'category': 'Food',
        'payment_type': 'Cash',
    })
    resp = auth_client.post('/chat',
                            data=json.dumps({'question': 'what is my total'}),
                            content_type='application/json')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'total' in data['answer'].lower() or '₹' in data['answer']


def test_chat_target(auth_client):
    resp = auth_client.post('/chat',
                            data=json.dumps({'question': 'what is my target'}),
                            content_type='application/json')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'target' in data['answer'].lower()
