from app.utils import parse_sms, parse_receipt, generate_insights
from app.models import Expense, db

def test_parse_sms():
    text = "Spent Rs. 500 via UPI at Starbucks"
    result = parse_sms(text)
    assert result['amount'] == 500.0
    assert result['merchant'] == 'Starbucks'
    assert result['payment_type'] == 'UPI'

def test_parse_receipt():
    text = "Store: Walmart\nAmount: $ 120.50\nDate: 2026-06-05\nCard payment"
    result = parse_receipt(text)
    assert result['amount'] == 120.50
    assert result['merchant'] == 'Walmart'
    assert result['payment_type'] == 'Card'

def test_generate_insights_empty(app, auth_client):
    with app.app_context():
        res = generate_insights(999) # user with no expenses
        assert res['total_spending'] == 0
        assert 'No expenses recorded yet.' in res['warnings']

def test_generate_insights_with_data(app, auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-06-01',
        'merchant': 'McDonalds',
        'amount': '40000', # large amount to trigger warnings
        'category': 'Food',
        'payment_type': 'Card'
    })
    
    with app.app_context():
        res = generate_insights(1) # test user id is 1
        assert res['total_spending'] >= 40000
        assert 'Food' in res['category_breakdown']
        assert any('income' in w.lower() for w in res['warnings'])
