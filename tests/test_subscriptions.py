from app.models import Subscription


def test_subscriptions_view(auth_client):
    resp = auth_client.get('/subscriptions')
    assert resp.status_code == 200


def test_add_subscription(auth_client):
    resp = auth_client.post('/subscriptions', data={
        'merchant': 'Netflix',
        'amount': '15.99',
        'category': 'Entertainment',
        'billing_cycle': 'monthly',
        'next_billing_date': '2026-06-01'
    }, follow_redirects=True)

    assert resp.status_code == 200
    sub = Subscription.query.filter_by(merchant='Netflix').first()
    assert sub is not None
    assert sub.merchant == 'Netflix'
    assert float(sub.amount) == 15.99


def test_delete_subscription(auth_client):
    auth_client.post('/subscriptions', data={
        'merchant': 'DeleteSub',
        'amount': '10.0',
        'category': 'Misc',
        'billing_cycle': 'yearly',
        'next_billing_date': '2026-06-01'
    })
    sub = Subscription.query.filter_by(merchant='DeleteSub').first()
    assert sub is not None

    resp = auth_client.post(
        f'/subscriptions/delete/{sub.id}', follow_redirects=True)
    assert resp.status_code == 200

    deleted_sub = Subscription.query.filter_by(merchant='DeleteSub').first()
    assert deleted_sub is None
