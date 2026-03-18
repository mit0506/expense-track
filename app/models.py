from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10))
    merchant = db.Column(db.String(100))
    amount = db.Column(db.Float)
    category = db.Column(db.String(50))
    payment_type = db.Column(db.String(50))

    def to_dict(self):
        return {
            'date': self.date,
            'merchant': self.merchant,
            'amount': self.amount,
            'category': self.category,
            'payment_type': self.payment_type
        }

    def __init__(self, date: str = '', merchant: str = '', amount: float = 0.0, category: str = 'Miscellaneous', payment_type: str = 'Cash'):
        self.date = date
        self.merchant = merchant
        self.amount = amount
        self.category = category
        self.payment_type = payment_type


class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default='User')
    monthly_income = db.Column(db.Float, default=0.0)
    monthly_target = db.Column(db.Float, default=0.0)  # expense target
    avatar = db.Column(db.String(200), nullable=True)  # filename or URL

    def to_dict(self):
        return {
            'name': self.name,
            'monthly_income': self.monthly_income,
            'monthly_target': self.monthly_target,
            'avatar': self.avatar
        }

    def __init__(self, name: str = 'User', monthly_income: float = 0.0, monthly_target: float = 0.0, avatar: str | None = None):
        self.name = name
        self.monthly_income = monthly_income
        self.monthly_target = monthly_target
        self.avatar = avatar
