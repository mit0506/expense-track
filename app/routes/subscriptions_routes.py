import logging
from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, Subscription
from app.constants import MAX_EXPENSE_AMOUNT
from app.routes import main_bp

logger = logging.getLogger(__name__)


@main_bp.route('/subscriptions', methods=['GET', 'POST'])
@login_required
def subscriptions():
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0 or amount > MAX_EXPENSE_AMOUNT:
            from flask import flash
            flash('Invalid amount.')
            return redirect(url_for('main.subscriptions'))

        merchant = request.form.get('merchant', '')[:100]
        category = request.form.get('category', 'Miscellaneous')
        billing_cycle = request.form.get('billing_cycle', 'monthly')
        next_billing_date = request.form.get('next_billing_date', '')

        sub = Subscription(
            user_id=current_user.id,
            merchant=merchant,
            amount=amount,
            category=category,
            billing_cycle=billing_cycle,
            next_billing_date=next_billing_date
        )
        db.session.add(sub)
        db.session.commit()
        return redirect(url_for('main.subscriptions'))

    subs = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.next_billing_date).all()
    return render_template('subscriptions.html', subscriptions=subs)


@main_bp.route('/subscriptions/delete/<int:sub_id>', methods=['POST'])
@login_required
def delete_subscription(sub_id):
    sub = Subscription.query.filter_by(id=sub_id, user_id=current_user.id).first_or_404()
    db.session.delete(sub)
    db.session.commit()
    return redirect(url_for('main.subscriptions'))
