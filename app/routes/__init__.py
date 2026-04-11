import logging
from datetime import datetime
from flask import Blueprint
from flask_login import current_user
from app.models import db, Expense, BillSplit, CategoryBudget
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

    # Budget alerts
    budget_alerts = []
    monthly_target = float(current_user.monthly_target or 0)
    total_float = float(total_spending)

    if monthly_target > 0:
        pct = (total_float / monthly_target) * 100
        if pct >= 100:
            budget_alerts.append({
                'level': 'critical',
                'message': f'Monthly target exceeded! Spent {pct:.0f}% of your budget.',
            })
        elif pct >= 90:
            budget_alerts.append({
                'level': 'warning',
                'message': f'At {pct:.0f}% of monthly target. Only ₹{monthly_target - total_float:.0f} remaining.',
            })
        elif pct >= 75:
            budget_alerts.append({
                'level': 'caution',
                'message': f'Approaching budget limit at {pct:.0f}%. ₹{monthly_target - total_float:.0f} left.',
            })

    # Category budget alerts
    cat_budgets = CategoryBudget.query.filter_by(user_id=current_user.id).all()
    if cat_budgets:
        cat_rows = (
            db.session.query(Expense.category, db.func.sum(Expense.amount))
            .filter(Expense.user_id == current_user.id, Expense.date.like(f'{prefix}%'))
            .group_by(Expense.category)
            .all()
        )
        cat_spending = {row[0]: float(row[1]) for row in cat_rows}
        for cb in cat_budgets:
            limit = float(cb.amount) if cb.amount else 0
            if limit <= 0:
                continue
            spent = cat_spending.get(cb.category, 0.0)
            cat_pct = (spent / limit) * 100
            if cat_pct >= 100:
                budget_alerts.append({
                    'level': 'critical',
                    'message': f'{cb.category} budget exceeded ({cat_pct:.0f}%).',
                })
            elif cat_pct >= 80:
                budget_alerts.append({
                    'level': 'warning',
                    'message': f'{cb.category} at {cat_pct:.0f}% of budget. ₹{limit - spent:.0f} left.',
                })

    return {
        'monthly_total': total_float,
        'net_balance': net_balance,
        'monthly_target_float': monthly_target,
        'monthly_income_float': float(current_user.monthly_income or 0),
        'budget_alerts': budget_alerts,
    }


# Import route modules to register their routes on main_bp
from app.routes import auth, expenses, subscriptions_routes, api  # noqa: E402, F401
