from app.models import Expense, UserProfile, CategoryBudget, Subscription, BillSplit


def test_user_profile_init():
    user = UserProfile(username="test", password_hash="hash",
                       name="Test", monthly_income=1000)
    assert user.username == "test"
    assert user.name == "Test"
    assert user.monthly_income == 1000
    d = user.to_dict()
    assert d['username'] == "test"
    assert d['monthly_income'] == 1000.0


def test_expense_init():
    exp = Expense(user_id=1, merchant="Store", amount=50.5, category="Food")
    assert exp.merchant == "Store"
    assert exp.amount == 50.5
    assert exp.category == "Food"
    d = exp.to_dict()
    assert d['merchant'] == "Store"
    assert d['amount'] == 50.5


def test_category_budget_init():
    cb = CategoryBudget(user_id=1, category="Food", amount=200)
    assert cb.category == "Food"
    assert cb.amount == 200
    d = cb.to_dict()
    assert d['category'] == "Food"
    assert d['amount'] == 200.0


def test_subscription_init():
    sub = Subscription(user_id=1, merchant="Netflix",
                       amount=15.99, next_billing_date="2026-06-01")
    assert sub.merchant == "Netflix"
    assert sub.amount == 15.99
    assert sub.billing_cycle == "monthly"


def test_billsplit_init():
    bs = BillSplit(expense_id=1, payer_id=1, debtor_id=2, amount=25.0)
    assert bs.payer_id == 1
    assert bs.debtor_id == 2
    assert bs.amount == 25.0
    assert bs.settled is False
