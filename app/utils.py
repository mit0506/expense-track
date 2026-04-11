import re
from datetime import datetime, timedelta
from flask import current_app
from app.models import Expense
from app.constants import CATEGORY_KEYWORDS


def _extract_date(text):
    date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if date_match:
        return date_match.group(1)
    date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
    if date_match:
        return date_match.group(1).replace('/', '-')
    return datetime.today().strftime('%Y-%m-%d')


def _extract_amount(text, currency_pattern):
    amount_match = re.search(currency_pattern, text, re.IGNORECASE)
    if amount_match:
        return float(amount_match.group(1))
    numbers = re.findall(r'\b(\d+(?:\.\d{2})?)\b', text)
    if numbers:
        return max(float(n) for n in numbers)
    return 0.0


def _infer_category(text):
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(word in text_lower for word in keywords):
            return category
    return 'Miscellaneous'


def _extract_payment_type(text):
    text_lower = text.lower()
    if 'upi' in text_lower:
        return 'UPI'
    if any(word in text_lower for word in ['card', 'debit', 'credit']):
        return 'Card'
    return 'Cash'


def parse_sms(text):
    date = _extract_date(text)
    amount = _extract_amount(text, r'(?:Rs\.?|INR|₹)\s*(\d+(?:\.\d{2})?)')

    merchant = 'Unknown'
    merchant_match = re.search(r'(?:from|at)\s+([A-Za-z\s]+)', text, re.IGNORECASE)
    if merchant_match:
        merchant = merchant_match.group(1).strip()

    return {
        'date': date,
        'merchant': merchant,
        'amount': amount,
        'category': _infer_category(text),
        'payment_type': _extract_payment_type(text),
    }


def parse_receipt(text):
    date = _extract_date(text)
    amount = _extract_amount(text, r'(?:Rs\.?|₹|\$)\s*(\d+(?:\.\d{2})?)')

    lines = text.split('\n')
    merchant = 'Unknown'
    for line in lines:
        if 'merchant' in line.lower() or 'store' in line.lower():
            merchant = line.split(':')[-1].strip()
            break
    if merchant == 'Unknown' and lines:
        merchant = lines[0].strip()

    category = _infer_category(text)
    if merchant != 'Unknown':
        merchant_lower = merchant.lower()
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(word in merchant_lower for word in keywords):
                category = cat
                break

    return {
        'date': date,
        'merchant': merchant,
        'amount': amount,
        'category': category,
        'payment_type': _extract_payment_type(text),
    }


def generate_insights(user_id):
    expenses = Expense.query.filter_by(user_id=user_id).all()
    expense_data = [e.to_dict() for e in expenses]

    if not expense_data:
        return {
            'total_spending': 0,
            'category_breakdown': {},
            'trends': [],
            'warnings': ['No expenses recorded yet.'],
            'recommendations': ['Start tracking your expenses to get insights.']
        }

    total_spending = sum(float(e.get('amount', 0)) for e in expense_data)

    category_totals: dict[str, float] = {}
    for e in expense_data:
        cat_key = str(e.get('category', 'Miscellaneous'))
        amt_val = float(e.get('amount', 0.0))
        category_totals[cat_key] = category_totals.get(cat_key, 0.0) + amt_val

    sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

    now = datetime.now()
    this_week_start = now - timedelta(days=now.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(days=1)

    this_month_start = now.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)

    this_week_spending: dict[str, float] = {}
    last_week_spending: dict[str, float] = {}
    this_month_spending: dict[str, float] = {}
    last_month_spending: dict[str, float] = {}

    for e in expense_data:
        date_str = str(e.get('date', ''))
        if not date_str:
            continue
        try:
            expense_date = datetime.strptime(date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            continue

        amt = float(e.get('amount', 0.0))
        cat = str(e.get('category', 'Miscellaneous'))
        if expense_date >= this_week_start:
            this_week_spending[cat] = this_week_spending.get(cat, 0.0) + amt
        elif last_week_start <= expense_date <= last_week_end:
            last_week_spending[cat] = last_week_spending.get(cat, 0.0) + amt

        if expense_date >= this_month_start:
            this_month_spending[cat] = this_month_spending.get(cat, 0.0) + amt
        elif last_month_start <= expense_date <= last_month_end:
            last_month_spending[cat] = last_month_spending.get(cat, 0.0) + amt

    trends: list[str] = []
    for category in set(this_week_spending) | set(last_week_spending):
        this_week = this_week_spending.get(category, 0.0)
        last_week = last_week_spending.get(category, 0.0)
        if last_week > 0.0:
            change = ((this_week - last_week) / last_week) * 100
            direction = 'increased' if change > 0 else 'decreased'
            trends.append(f"{category} spending {direction} by {abs(change):.1f}% this week.")

    for category in set(this_month_spending) | set(last_month_spending):
        this_month = this_month_spending.get(category, 0.0)
        last_month = last_month_spending.get(category, 0.0)
        if last_month > 0.0:
            change = ((this_month - last_month) / last_month) * 100
            direction = 'increased' if change > 0 else 'decreased'
            trends.append(f"{category} spending {direction} by {abs(change):.1f}% this month.")

    warnings: list[str] = []
    monthly_inc = float(current_app.config.get('MONTHLY_INCOME', 50000.0))
    if total_spending > (monthly_inc * 0.8):
        overall_perc = (total_spending / monthly_inc) * 100.0
        warnings.append(
            f"You've spent ₹{total_spending:.0f} which is {overall_perc:.1f}%"
            f" of your monthly income of ₹{monthly_inc}."
        )

    for category, amount in sorted_categories:
        if float(amount) > (monthly_inc * 0.3):
            cat_perc = (float(amount) / monthly_inc) * 100.0
            warnings.append(f"You're spending ₹{amount:.0f} on {category}, which is {cat_perc:.1f}% of your income.")

    recommendations: list[str] = []
    high_spending_categories = [cat for cat, amt in sorted_categories if float(amt) > (total_spending * 0.2)]
    for category in high_spending_categories:
        if category == 'Food':
            recommendations.append("Consider meal planning or cooking at home to reduce food expenses.")
        elif category == 'Transport':
            recommendations.append("Try using public transport or carpooling to save on transport costs.")
        elif category == 'Shopping':
            recommendations.append("Set a monthly shopping budget and stick to it to increase savings.")
        else:
            recommendations.append(f"Review your {category.lower()} expenses and look for cost-saving alternatives.")

    potential_savings = sum(float(amt) * 0.1 for _, amt in sorted_categories[:2])
    if potential_savings > 0.0:
        recommendations.append(
            f"Reducing spending by 10% on your top categories"
            f" could save you ₹{potential_savings:.0f} monthly."
        )

    return {
        'total_spending': total_spending,
        'category_breakdown': dict(sorted_categories),
        'trends': trends,
        'warnings': warnings,
        'recommendations': recommendations
    }
