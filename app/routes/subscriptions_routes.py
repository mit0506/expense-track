import logging
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Subscription
from app.validators import validate_amount, validate_category, validate_date, validate_billing_cycle, sanitize_string
from app.routes import main_bp

logger = logging.getLogger(__name__)


@main_bp.route('/subscriptions', methods=['GET', 'POST'])
@login_required
def subscriptions():
    if request.method == 'POST':
        amount = validate_amount(request.form.get('amount', 0))
        if amount is None:
            flash('Invalid amount.')
            return redirect(url_for('main.subscriptions'))

        merchant = sanitize_string(request.form.get('merchant', ''), max_length=100)
        if not merchant:
            flash('Merchant name is required.')
            return redirect(url_for('main.subscriptions'))

        category = validate_category(request.form.get('category', 'Miscellaneous'))
        billing_cycle = validate_billing_cycle(request.form.get('billing_cycle', 'monthly'))
        next_billing_date = validate_date(request.form.get('next_billing_date', ''))
        if next_billing_date is None:
            flash('Invalid billing date.')
            return redirect(url_for('main.subscriptions'))

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
