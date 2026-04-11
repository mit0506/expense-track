import re
from datetime import datetime
from app.constants import EXPENSE_CATEGORIES, PAYMENT_TYPES, MAX_EXPENSE_AMOUNT


def validate_amount(raw_value):
    """Validate and return a float amount, or None if invalid."""
    try:
        amount = float(raw_value)
    except (ValueError, TypeError):
        return None
    if amount <= 0 or amount > MAX_EXPENSE_AMOUNT:
        return None
    return amount


def validate_category(category):
    """Return a valid category or default to Miscellaneous."""
    if category in EXPENSE_CATEGORIES:
        return category
    return 'Miscellaneous'


def validate_payment_type(payment_type):
    """Return a valid payment type or default to Cash."""
    if payment_type in PAYMENT_TYPES:
        return payment_type
    return 'Cash'


def validate_date(date_str):
    """Validate a YYYY-MM-DD date string. Returns the string or None."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        datetime.strptime(date_str.strip(), '%Y-%m-%d')
        return date_str.strip()
    except (ValueError, TypeError):
        return None


def sanitize_string(value, max_length=100):
    """Strip and truncate a string input."""
    if not value or not isinstance(value, str):
        return ''
    # Remove null bytes and control characters
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return cleaned.strip()[:max_length]


def validate_username(username):
    """Validate username: alphanumeric + underscores, 3-100 chars."""
    if not username or not isinstance(username, str):
        return None, 'Username is required.'
    username = username.strip()
    if len(username) < 3 or len(username) > 100:
        return None, 'Username must be between 3 and 100 characters.'
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return None, 'Username can only contain letters, numbers, and underscores.'
    return username, None


def validate_password(password):
    """Validate password: minimum 6 characters."""
    if not password or len(password) < 6:
        return None, 'Password must be at least 6 characters.'
    if len(password) > 128:
        return None, 'Password must be at most 128 characters.'
    return password, None


def validate_billing_cycle(cycle):
    """Validate billing cycle value."""
    valid = {'weekly', 'monthly', 'yearly'}
    if cycle in valid:
        return cycle
    return 'monthly'
