import re
import os
from datetime import datetime, timedelta
from flask import current_app
from app.models import Expense, UserProfile

def parse_sms(text):
    # Similar to parse_receipt but for SMS text
    # Date: look for YYYY-MM-DD or DD/MM/YYYY etc.
    date = None
    date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if date_match:
        date = date_match.group(1)
    else:
        date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        if date_match:
            date = date_match.group(1).replace('/', '-')

    if not date:
        date = datetime.today().strftime('%Y-%m-%d')  # Default to today

    # Merchant: look for common patterns in SMS like "from" or "at"
    merchant = 'Unknown'
    merchant_match = re.search(r'(?:from|at)\s+([A-Za-z\s]+)', text, re.IGNORECASE)
    if merchant_match:
        merchant = merchant_match.group(1).strip()

    # Amount: look for numbers with decimal, possibly with Rs or INR
    amount = 0.0
    amount_match = re.search(r'(?:Rs\.?|INR|₹)\s*(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
    if amount_match:
        amount = float(amount_match.group(1))
    else:
        # Look for any number that might be amount
        numbers = re.findall(r'\b(\d+(?:\.\d{2})?)\b', text)
        if numbers:
            # Assume the largest number is the amount
            amount = max(float(n) for n in numbers)

    # Category: inference based on keywords
    category = 'Miscellaneous'
    if any(word in text.lower() for word in ['food', 'restaurant', 'pizza', 'burger', 'cafe']):
        category = 'Food'
    elif any(word in text.lower() for word in ['taxi', 'uber', 'ola', 'transport', 'cab']):
        category = 'Transport'
    elif any(word in text.lower() for word in ['amazon', 'flipkart', 'shopping', 'store']):
        category = 'Shopping'

    # Payment Type: look for UPI, Card, Cash, Debit
    payment_type = 'Cash'
    if 'upi' in text.lower():
        payment_type = 'UPI'
    elif any(word in text.lower() for word in ['card', 'debit', 'credit']):
        payment_type = 'Card'

    return {
        'date': date,
        'merchant': merchant,
        'amount': amount,
        'category': category,
        'payment_type': payment_type
    }

def parse_receipt(text):
    # Simple NLP parsing with regex
    # Date: look for YYYY-MM-DD or DD/MM/YYYY etc.
    date = None
    date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if date_match:
        date = date_match.group(1)
    else:
        date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        if date_match:
            date = date_match.group(1).replace('/', '-')

    if not date:
        date = datetime.today().strftime('%Y-%m-%d')

    # Merchant: assume first line or after 'Merchant' or store name
    lines = text.split('\n')
    merchant = 'Unknown'
    for line in lines:
        if 'merchant' in line.lower() or 'store' in line.lower():
            merchant = line.split(':')[-1].strip()
            break
    if merchant == 'Unknown' and lines:
        merchant = lines[0].strip()

    # Amount: look for numbers with decimal, possibly with Rs or $
    amount = 0.0
    amount_match = re.search(r'(?:Rs\.?|₹|\$)\s*(\d+(?:\.\d{2})?)', text)
    if amount_match:
        amount = float(amount_match.group(1))
    else:
        amount_match = re.search(r'\b(\d+(?:\.\d{2})?)\b', text)
        if amount_match:
            amount = float(amount_match.group(1))

    # Category: simple inference based on merchant
    category = 'Miscellaneous'
    if 'domino' in merchant.lower() or 'food' in text.lower():
        category = 'Food'
    elif 'uber' in merchant.lower() or 'taxi' in text.lower():
        category = 'Transport'

    # Payment Type: look for UPI, Card, Cash
    payment_type = 'Cash'
    if 'upi' in text.lower():
        payment_type = 'UPI'
    elif 'card' in text.lower():
        payment_type = 'Card'

    return {
        'date': date,
        'merchant': merchant,
        'amount': amount,
        'category': category,
        'payment_type': payment_type
    }

def generate_insights():
    # Get all expenses
    expenses = Expense.query.all()
    expense_data = [e.to_dict() for e in expenses]

    if not expense_data:
        return {
            'total_spending': 0,
            'category_breakdown': {},
            'trends': [],
            'warnings': ['No expenses recorded yet.'],
            'recommendations': ['Start tracking your expenses to get insights.']
        }

    # Calculate total spending
    total_spending: float = 0.0
    for e in expense_data:
        total_spending = total_spending + float(e.get('amount', 0.0))

    # Category breakdown
    category_totals: dict[str, float] = {}
    for e in expense_data:
        cat_key = str(e.get('category', 'Miscellaneous'))
        amt_val = float(e.get('amount', 0.0))
        category_totals[cat_key] = category_totals.get(cat_key, 0.0) + amt_val

    # Sort categories by spending
    sorted_categories: list[tuple[str, float]] = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

    # Trends analysis (compare this week vs last week, this month vs last month)
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

    # Calculate trends
    trends: list[str] = []
    all_categories = set(list(this_week_spending.keys()) + list(last_week_spending.keys()))
    for category in all_categories:
        this_week = float(this_week_spending.get(category, 0.0))
        last_week = float(last_week_spending.get(category, 0.0))
        if last_week > 0.0:
            change = ((this_week - last_week) / last_week) * 100
            trends.append(f"{category} spending {'increased' if change > 0 else 'decreased'} by {abs(change):.1f}% this week.")

    month_categories = set(list(this_month_spending.keys()) + list(last_month_spending.keys()))
    for category in month_categories:
        this_month = float(this_month_spending.get(category, 0.0))
        last_month = float(last_month_spending.get(category, 0.0))
        if last_month > 0.0:
            change = ((this_month - last_month) / last_month) * 100
            trends.append(f"{category} spending {'increased' if change > 0 else 'decreased'} by {abs(change):.1f}% this month.")

    # Warnings
    warnings: list[str] = []
    monthly_inc_lookup: float = float(current_app.config.get('MONTHLY_INCOME', 50000.0))
    if float(total_spending) > (monthly_inc_lookup * 0.8):
        overall_perc: float = (float(total_spending) / monthly_inc_lookup) * 100.0
        warnings.append(f"You've spent ₹{total_spending:.0f} which is {overall_perc:.1f}% of your monthly income of ₹{monthly_inc_lookup}.")

    for category, amount in sorted_categories:
        if float(amount) > (monthly_inc_lookup * 0.3):  # More than 30% on one category
            cat_perc: float = (float(amount) / monthly_inc_lookup) * 100.0
            warnings.append(f"You're spending ₹{amount:.0f} on {category}, which is {cat_perc:.1f}% of your income.")

    # Recommendations
    recommendations: list[str] = []
    high_spending_categories = [cat for cat, amt in sorted_categories if float(amt) > (float(total_spending) * 0.2)]
    for category in high_spending_categories:
        if category == 'Food':
            recommendations.append("Consider meal planning or cooking at home to reduce food expenses.")
        elif category == 'Transport':
            recommendations.append("Try using public transport or carpooling to save on transport costs.")
        elif category == 'Shopping':
            recommendations.append("Set a monthly shopping budget and stick to it to increase savings.")
        else:
            recommendations.append(f"Review your {category.lower()} expenses and look for cost-saving alternatives.")

    # savings potential (manual loop for first 2 to satisfy IDE)
    potential_savings: float = 0.0
    count: int = 0
    for cat, amt in sorted_categories:
        if count >= 2:
            break
        potential_savings = potential_savings + (float(amt) * 0.1)
        count = count + 1

    if potential_savings > 0.0:
        recommendations.append(f"Reducing spending by 10% on your top categories could save you ₹{potential_savings:.0f} monthly.")

    return {
        'total_spending': total_spending,
        'category_breakdown': dict(sorted_categories),
        'trends': trends,
        'warnings': warnings,
        'recommendations': recommendations
    }
