from __future__ import annotations
from typing import Optional, List
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import Numeric, String, Integer, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()


class Expense(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('user_profile.id'), index=True)
    date: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    merchant: Mapped[Optional[str]] = mapped_column(String(100))
    amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    category: Mapped[Optional[str]] = mapped_column(String(50))
    payment_type: Mapped[Optional[str]] = mapped_column(String(50))

    user: Mapped["UserProfile"] = relationship(back_populates="expenses")

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

    def __init__(
        self, user_id, date: str = '', merchant: str = '',
        amount: float = 0.0, category: str = 'Miscellaneous', payment_type: str = 'Cash'
    ):
        self.user_id = user_id
        self.date = date
        self.merchant = merchant
        self.amount = amount
        self.category = category
        self.payment_type = payment_type


class CategoryBudget(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('user_profile.id'), index=True)
    category: Mapped[str] = mapped_column(String(50))
    amount: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), default=0.0)

    __table_args__ = (UniqueConstraint(
        'user_id', 'category', name='_user_category_uc'),)

    def to_dict(self):
        return {'category': self.category, 'amount': float(self.amount) if self.amount else 0.0}

    def __init__(self, user_id, category, amount=0.0):
        self.user_id = user_id
        self.category = category
        self.amount = amount


class Subscription(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('user_profile.id'), index=True)
    merchant: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    category: Mapped[Optional[str]] = mapped_column(String(50))
    billing_cycle: Mapped[Optional[str]] = mapped_column(
        String(20), default='monthly')
    next_billing_date: Mapped[str] = mapped_column(String(20))
    auto_log: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    last_processed: Mapped[Optional[str]] = mapped_column(String(20))

    def __init__(
        self, user_id, merchant, amount, category=None,
        billing_cycle='monthly', next_billing_date='',
        auto_log=True, last_processed=None
    ):
        self.user_id = user_id
        self.merchant = merchant
        self.amount = amount
        self.category = category
        self.billing_cycle = billing_cycle
        self.next_billing_date = next_billing_date
        self.auto_log = auto_log
        self.last_processed = last_processed


class BillSplit(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('expense.id'), index=True)
    payer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('user_profile.id'), index=True)
    debtor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('user_profile.id'), index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    settled: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    def __init__(self, expense_id, payer_id, debtor_id, amount, settled=False):
        self.expense_id = expense_id
        self.payer_id = payer_id
        self.debtor_id = debtor_id
        self.amount = amount
        self.settled = settled


class UserProfile(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(100), default='User')
    monthly_income: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), default=0.0)
    monthly_target: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), default=0.0)
    avatar: Mapped[Optional[str]] = mapped_column(String(200))

    expenses: Mapped[List["Expense"]] = relationship(
        back_populates="user", cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'monthly_income': float(self.monthly_income) if self.monthly_income else 0.0,
            'monthly_target': float(self.monthly_target) if self.monthly_target else 0.0,
            'avatar': self.avatar
        }

    def __init__(
        self, username, password_hash, name: str = 'User',
        monthly_income: float = 0.0, monthly_target: float = 0.0,
        avatar: str | None = None
    ):
        self.username = username
        self.password_hash = password_hash
        self.name = name
        self.monthly_income = monthly_income
        self.monthly_target = monthly_target
        self.avatar = avatar
