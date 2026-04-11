import logging
from datetime import datetime, timedelta
from app.models import db, Expense, Subscription

logger = logging.getLogger(__name__)


def _advance_date(current_date, billing_cycle):
    """Advance a date by one billing cycle period."""
    if billing_cycle == 'weekly':
        return current_date + timedelta(days=7)
    elif billing_cycle == 'monthly':
        month = current_date.month % 12 + 1
        year = current_date.year + (current_date.month // 12)
        day = current_date.day
        while True:
            try:
                return current_date.replace(year=year, month=month, day=day)
            except ValueError:
                day -= 1
    elif billing_cycle == 'yearly':
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            # Feb 29 -> Feb 28 in non-leap year
            return current_date.replace(year=current_date.year + 1, day=28)
    return None


def process_subscriptions(user_id):
    today = datetime.today().date()
    today_str = today.strftime('%Y-%m-%d')
    subs = Subscription.query.filter_by(user_id=user_id, auto_log=True).all()

    for sub in subs:
        if not sub.next_billing_date:
            continue

        # Skip if already processed today
        if sub.last_processed == today_str:
            continue

        try:
            next_date = datetime.strptime(sub.next_billing_date, '%Y-%m-%d').date()

            logged_any = False
            # Safety limit: max 52 iterations to prevent infinite loops
            iterations = 0
            while next_date <= today and iterations < 52:
                iterations += 1
                new_exp = Expense(
                    user_id=user_id,
                    date=next_date.strftime('%Y-%m-%d'),
                    merchant=sub.merchant,
                    amount=float(sub.amount),
                    category=sub.category,
                    payment_type='Auto (Sub)'
                )
                db.session.add(new_exp)
                logged_any = True

                advanced = _advance_date(next_date, sub.billing_cycle)
                if advanced is None or advanced <= next_date:
                    break
                next_date = advanced

            sub.next_billing_date = next_date.strftime('%Y-%m-%d')
            if logged_any:
                sub.last_processed = today_str

        except (ValueError, TypeError) as e:
            logger.warning("Error processing subscription %s: %s", sub.id, e)

    db.session.commit()
