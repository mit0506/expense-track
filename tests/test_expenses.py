from app.models import Expense, db


def test_add_manual_expense(auth_client):
    resp = auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'Test Store',
        'amount': '150.50',
        'category': 'Food',
        'payment_type': 'UPI',
    }, follow_redirects=True)
    assert resp.status_code == 200
    expense = Expense.query.filter_by(merchant='Test Store').first()
    assert expense is not None
    assert float(expense.amount) == 150.50
    assert expense.category == 'Food'


def test_add_expense_invalid_amount(auth_client):
    resp = auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'Bad Amount',
        'amount': '-50',
        'category': 'Food',
        'payment_type': 'Cash',
    }, follow_redirects=True)
    assert b'Invalid amount' in resp.data


def test_add_expense_zero_amount(auth_client):
    resp = auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'Zero',
        'amount': '0',
        'category': 'Food',
        'payment_type': 'Cash',
    }, follow_redirects=True)
    assert b'Invalid amount' in resp.data


def test_add_expense_invalid_category_defaults(auth_client):
    resp = auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'CatTest',
        'amount': '100',
        'category': 'InvalidCategory',
        'payment_type': 'Cash',
    }, follow_redirects=True)
    assert resp.status_code == 200
    expense = Expense.query.filter_by(merchant='CatTest').first()
    assert expense is not None
    assert expense.category == 'Miscellaneous'


def test_edit_expense(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'EditMe',
        'amount': '100',
        'category': 'Food',
        'payment_type': 'Cash',
    })
    expense = Expense.query.filter_by(merchant='EditMe').first()
    assert expense is not None
    resp = auth_client.post(f'/edit/{expense.id}', data={
        'date': '2026-04-02',
        'merchant': 'EditedStore',
        'amount': '200',
        'category': 'Transport',
        'payment_type': 'UPI',
    }, follow_redirects=True)
    assert resp.status_code == 200
    updated = Expense.query.get(expense.id)
    assert updated is not None
    assert updated.merchant == 'EditedStore'
    assert float(updated.amount) == 200.0


def test_delete_expense(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'DeleteMe',
        'amount': '50',
        'category': 'Food',
        'payment_type': 'Cash',
    })
    expense = Expense.query.filter_by(merchant='DeleteMe').first()
    assert expense is not None
    resp = auth_client.post(f'/delete/{expense.id}', follow_redirects=True)
    assert resp.status_code == 200
    assert Expense.query.get(expense.id) is None


def test_delete_other_users_expense(auth_client, app):
    """Cannot delete another user's expense."""
    from werkzeug.security import generate_password_hash
    from app.models import UserProfile
    other = UserProfile(
        username='other', password_hash=generate_password_hash('pass123'))
    db.session.add(other)
    db.session.flush()
    exp = Expense(user_id=other.id, date='2026-04-01',
                  merchant='NotYours', amount=100)
    db.session.add(exp)
    db.session.commit()
    exp_id = exp.id

    resp = auth_client.post(f'/delete/{exp_id}')
    assert resp.status_code == 404


def test_export_csv(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'CSV Store',
        'amount': '75',
        'category': 'Shopping',
        'payment_type': 'Card',
    })
    resp = auth_client.get('/export_csv')
    assert resp.status_code == 200
    assert resp.content_type == 'text/csv; charset=utf-8'
    assert b'CSV Store' in resp.data


def test_index_pagination(auth_client):
    resp = auth_client.get('/')
    assert resp.status_code == 200
    resp2 = auth_client.get('/?page=1')
    assert resp2.status_code == 200


def test_export_pdf(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'PDF Store',
        'amount': '75',
        'category': 'Shopping',
        'payment_type': 'Card',
    })
    resp = auth_client.get('/export_pdf')
    assert resp.status_code == 200
    assert resp.content_type == 'application/pdf'


def test_split_expense_view(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'Split Store',
        'amount': '100',
        'category': 'Food',
        'payment_type': 'Card',
    })
    from app.models import Expense
    expense = Expense.query.filter_by(merchant='Split Store').first()
    assert expense is not None
    resp = auth_client.get(f'/split/{expense.id}')
    assert resp.status_code == 200


def test_split_expense_post(auth_client, app):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'Split Post Store',
        'amount': '100',
        'category': 'Food',
        'payment_type': 'Card',
    })
    from app.models import Expense, db, UserProfile
    expense = Expense.query.filter_by(merchant='Split Post Store').first()
    assert expense is not None

    # Create another user to split with
    other = UserProfile(username='other_user', password_hash='hash')
    db.session.add(other)
    db.session.commit()

    resp = auth_client.post(f'/split/{expense.id}', data={
        'debtor_id': str(other.id),
        'amount': '50.0'
    }, follow_redirects=True)
    assert resp.status_code == 200

    from app.models import BillSplit
    split = BillSplit.query.filter_by(expense_id=expense.id).first()
    assert split is not None
    assert float(split.amount) == 50.0


def test_settle_split(auth_client, app):
    from app.models import Expense, db, UserProfile, BillSplit
    other = UserProfile.query.filter_by(username='other_user').first()
    if not other:
        other = UserProfile(username='other_user', password_hash='hash')
        db.session.add(other)
        db.session.commit()

    exp = Expense(user_id=1, merchant='Settle Store', amount=100)
    db.session.add(exp)
    db.session.commit()

    split = BillSplit(expense_id=exp.id, payer_id=1,
                      debtor_id=other.id, amount=50.0)
    db.session.add(split)
    db.session.commit()

    resp = auth_client.post(f'/settle/{split.id}', follow_redirects=True)
    assert resp.status_code == 200

    updated_split = BillSplit.query.get(split.id)
    assert updated_split is not None
    assert updated_split.settled is True
