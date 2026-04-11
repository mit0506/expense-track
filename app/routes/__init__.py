import logging
from datetime import datetime
from flask import Blueprint
from flask_login import current_user
from app.models import db, Expense, BillSplit
from app.routes.subscriptions import process_subscriptions

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.context_processor
def inject_global_data():
    if not current_user.is_authenticated:
        return {'monthly_total': 0.0}

    process_subscriptions(current_user.id)

    # Use DB aggregation instead of loading all expenses into memory
    today = datetime.today()
    prefix = today.strftime('%Y-%m')
    total_spending = (
        db.session.query(db.func.sum(Expense.amount))
        .filter(Expense.user_id == current_user.id, Expense.date.like(f'{prefix}%'))
        .scalar()
    ) or 0.0

    i_owe = (
        db.session.query(db.func.sum(BillSplit.amount))
        .filter_by(debtor_id=current_user.id, settled=False)
        .scalar()
    ) or 0.0
    owed_to_me = (
        db.session.query(db.func.sum(BillSplit.amount))
        .filter_by(payer_id=current_user.id, settled=False)
        .scalar()
    ) or 0.0
    net_balance = float(owed_to_me) - float(i_owe)

    return {
        'monthly_total': float(total_spending),
        'net_balance': net_balance,
        'monthly_target_float': float(current_user.monthly_target or 0),
        'monthly_income_float': float(current_user.monthly_income or 0),
    }


# Import route modules to register their routes on main_bp
from app.routes import auth, expenses, subscriptions_routes, api  # noqa: E402, F401
