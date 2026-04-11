import logging
from datetime import datetime
from app.models import db, Expense, Subscription

logger = logging.getLogger(__name__)


def process_subscriptions(user_id):
    today = datetime.today().date()
    subs = Subscription.query.filter_by(user_id=user_id, auto_log=True).all()
    for sub in subs:
        if not sub.next_billing_date:
            continue
        try:
            next_date = datetime.strptime(sub.next_billing_date, '%Y-%m-%d').date()
            while next_date <= today:
                new_exp = Expense(
                    user_id=user_id,
                    date=next_date.strftime('%Y-%m-%d'),
                    merchant=sub.merchant,
                    amount=float(sub.amount),
                    category=sub.category,
                    payment_type='Auto (Sub)'
                )
                db.session.add(new_exp)

                if sub.billing_cycle == 'monthly':
                    month = next_date.month % 12 + 1
                    year = next_date.year + (next_date.month // 12)
                    day = next_date.day
                    while True:
                        try:
                            next_date = next_date.replace(year=year, month=month, day=day)
                            break
                        except ValueError:
                            day -= 1
                elif sub.billing_cycle == 'yearly':
                    next_date = next_date.replace(year=next_date.year + 1)
                else:
                    break

            sub.next_billing_date = next_date.strftime('%Y-%m-%d')
        except (ValueError, TypeError) as e:
            logger.warning("Error processing subscription %s: %s", sub.id, e)
    db.session.commit()
