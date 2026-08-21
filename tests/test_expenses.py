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


def test_htmx_expense_table(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'HTMX Table Store',
        'amount': '250.0',
        'category': 'Shopping',
        'payment_type': 'Card',
    })
    resp = auth_client.get('/expenses/table', headers={'HX-Request': 'true'})
    assert resp.status_code == 200
    assert b'HTMX Table Store' in resp.data
    assert b'expense-row-' in resp.data


def test_htmx_expense_table_filter(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'Groceries Alpha',
        'amount': '300.0',
        'category': 'Food',
        'payment_type': 'Cash',
    })
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'Metro Ride',
        'amount': '50.0',
        'category': 'Transport',
        'payment_type': 'UPI',
    })
    # Filter by category Food
    resp = auth_client.get('/expenses/table?category=Food', headers={'HX-Request': 'true'})
    assert resp.status_code == 200
    assert b'Groceries Alpha' in resp.data
    assert b'Metro Ride' not in resp.data

    # Filter by search
    resp_search = auth_client.get('/expenses/table?search=Metro', headers={'HX-Request': 'true'})
    assert resp_search.status_code == 200
    assert b'Metro Ride' in resp_search.data
    assert b'Groceries Alpha' not in resp_search.data


def test_htmx_get_expense_row(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'Row Test',
        'amount': '80.0',
        'category': 'Health',
        'payment_type': 'Cash',
    })
    expense = Expense.query.filter_by(merchant='Row Test').first()
    assert expense is not None
    resp = auth_client.get(f'/expenses/{expense.id}/row', headers={'HX-Request': 'true'})
    assert resp.status_code == 200
    assert b'Row Test' in resp.data


def test_htmx_add_manual(auth_client):
    resp = auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'HTMX Add Store',
        'amount': '42.0',
        'category': 'Entertainment',
        'payment_type': 'UPI',
    }, headers={'HX-Request': 'true'})
    assert resp.status_code == 200
    assert b'HTMX Add Store' in resp.data
    assert b'id="expense-row-' in resp.data


def test_htmx_edit_expense_get_and_post(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'HTMX Edit Target',
        'amount': '99.0',
        'category': 'Utilities',
        'payment_type': 'Cash',
    })
    expense = Expense.query.filter_by(merchant='HTMX Edit Target').first()
    assert expense is not None

    # GET inline edit form
    resp_form = auth_client.get(f'/expenses/{expense.id}/edit', headers={'HX-Request': 'true'})
    assert resp_form.status_code == 200
    assert b'name="merchant"' in resp_form.data
    assert b'HTMX Edit Target' in resp_form.data

    # POST updated data
    resp_post = auth_client.post(f'/expenses/{expense.id}/edit', data={
        'date': '2026-04-05',
        'merchant': 'HTMX Edited Name',
        'amount': '150.0',
        'category': 'Utilities',
        'payment_type': 'UPI',
    }, headers={'HX-Request': 'true'})
    assert resp_post.status_code == 200
    assert b'HTMX Edited Name' in resp_post.data


def test_htmx_delete_expense(auth_client):
    auth_client.post('/add_manual', data={
        'date': '2026-04-01',
        'merchant': 'HTMX Delete Target',
        'amount': '12.0',
        'category': 'Food',
        'payment_type': 'Cash',
    })
    expense = Expense.query.filter_by(merchant='HTMX Delete Target').first()
    assert expense is not None

    resp = auth_client.delete(f'/expenses/{expense.id}', headers={'HX-Request': 'true'})
    assert resp.status_code == 200
    assert resp.data == b''
    assert Expense.query.get(expense.id) is None


def test_htmx_add_sms_parse(auth_client):
    sms = "Spent Rs. 450.00 at Starbucks on 2026-04-01 using UPI."
    resp = auth_client.post('/add_sms', data={'sms_text': sms}, headers={'HX-Request': 'true'})
    assert resp.status_code == 200
    assert b'sms-result-container' in resp.data
    assert b'Starbucks' in resp.data

