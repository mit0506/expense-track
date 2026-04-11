from __future__ import annotations
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import Numeric

db = SQLAlchemy()

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_profile.id'), nullable=False, index=True)
    date = db.Column(db.String(10), index=True)
    merchant = db.Column(db.String(100))
    amount = db.Column(Numeric(10, 2))
    category = db.Column(db.String(50))
    payment_type = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date,
            'merchant': self.merchant,
            'amount': float(self.amount) if self.amount else 0.0,
            'category': self.category,
            'payment_type': self.payment_type
        }

    def __init__(self, user_id, date: str = '', merchant: str = '', amount: float = 0.0, category: str = 'Miscellaneous', payment_type: str = 'Cash'):
        self.user_id = user_id
        self.date = date
        self.merchant = merchant
        self.amount = amount
        self.category = category
        self.payment_type = payment_type

class CategoryBudget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_profile.id'), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(Numeric(10, 2), default=0.0)
    __table_args__ = (db.UniqueConstraint('user_id', 'category', name='_user_category_uc'),)

    def to_dict(self):
        return {'category': self.category, 'amount': float(self.amount) if self.amount else 0.0}

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_profile.id'), nullable=False, index=True)
    merchant = db.Column(db.String(100), nullable=False)
    amount = db.Column(Numeric(10, 2), nullable=False)
    category = db.Column(db.String(50))
    billing_cycle = db.Column(db.String(20), default='monthly')
    next_billing_date = db.Column(db.String(20), nullable=False)
    auto_log = db.Column(db.Boolean, default=True)
    last_processed = db.Column(db.String(20), nullable=True)

class BillSplit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=False, index=True)
    payer_id = db.Column(db.Integer, db.ForeignKey('user_profile.id'), nullable=False, index=True)
    debtor_id = db.Column(db.Integer, db.ForeignKey('user_profile.id'), nullable=False, index=True)
    amount = db.Column(Numeric(10, 2), nullable=False)
    settled = db.Column(db.Boolean, default=False)

class UserProfile(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), default='User')
    monthly_income = db.Column(Numeric(10, 2), default=0.0)
    monthly_target = db.Column(Numeric(10, 2), default=0.0)
    avatar = db.Column(db.String(200), nullable=True)
    expenses = db.relationship('Expense', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'monthly_income': float(self.monthly_income) if self.monthly_income else 0.0,
            'monthly_target': float(self.monthly_target) if self.monthly_target else 0.0,
            'avatar': self.avatar
        }

    def __init__(self, username, password_hash, name: str = 'User', monthly_income: float = 0.0, monthly_target: float = 0.0, avatar: str | None = None):
        self.username = username
        self.password_hash = password_hash
        self.name = name
        self.monthly_income = monthly_income
        self.monthly_target = monthly_target
        self.avatar = avatar
