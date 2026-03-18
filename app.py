from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import pytesseract
from pytesseract import TesseractNotFoundError
from PIL import Image
import re
import os
from datetime import datetime, timedelta
import calendar

# optional AI chatbot integration
try:
    import openai  # type: ignore[import]
    # read API key from environment variable
    openai.api_key = os.environ.get('OPENAI_API_KEY', '')
except ImportError:
    openai = None

# Try to set Tesseract path if it exists in common Windows locations
try:
    if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
        setattr(pytesseract, 'pytesseract_cmd', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    elif os.path.exists(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
        setattr(pytesseract, 'pytesseract_cmd', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe')
except Exception:
    pass  # Tesseract will be auto-detected from PATH

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MONTHLY_INCOME'] = 50000  # Default monthly income, can be configured
db = SQLAlchemy(app)

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

@app.route('/')
def index():
    expenses = Expense.query.all()
    # check monthly target
    profile = UserProfile.query.first()
    target_exceeded: bool = False
    today = datetime.today()
    prefix = today.strftime('%Y-%m')  # e.g. '2026-03'
    
    total_monthly_spending: float = 0.0
    for exp in expenses:
        if exp and exp.date and exp.date.startswith(prefix):
            total_monthly_spending = total_monthly_spending + float(exp.amount or 0.0)

    if profile and profile.monthly_target and total_monthly_spending > float(profile.monthly_target):
        target_exceeded = True
    return render_template('index.html', expenses=expenses, target_exceeded=target_exceeded, monthly_total=total_monthly_spending)

# make profile data and monthly total available globally
@app.context_processor
def inject_global_data():
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile(name='User', monthly_income=app.config.get('MONTHLY_INCOME', 0))
        db.session.add(profile)
        db.session.commit()
    
    # Calculate monthly total once for all templates
    expenses = Expense.query.all()
    today = datetime.today()
    prefix = today.strftime('%Y-%m')
    total_spending_current_month: float = 0.0
    for exp in expenses:
        if exp and exp.date and exp.date.startswith(prefix):
            total_spending_current_month = total_spending_current_month + float(exp.amount or 0.0)
                
    return {
        'user_profile': profile,
        'monthly_total': total_spending_current_month
    }

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # allow user to set name, income, monthly expense target, and avatar
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile(
            name='User',
            monthly_income=app.config.get('MONTHLY_INCOME', 0),
            monthly_target=0.0,
            avatar=None
        )
        db.session.add(profile)
        db.session.commit()
    if request.method == 'POST':
        profile.name = request.form.get('name', profile.name)
        try:
            profile.monthly_income = float(request.form.get('monthly_income', profile.monthly_income))
        except ValueError:
            pass
        try:
            profile.monthly_target = float(request.form.get('monthly_target', profile.monthly_target))
        except ValueError:
            pass
        # handle avatar upload
        file = request.files.get('avatar')
        if file and file.filename:
            filename = file.filename
            avatar_dir = os.path.join(str(app.static_folder), 'avatars')
            if not os.path.exists(avatar_dir):
                os.makedirs(avatar_dir)
            filepath = os.path.join(avatar_dir, filename)
            file.save(filepath)
            profile.avatar = filename
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('profile.html', profile=profile)


@app.route('/add_manual', methods=['GET', 'POST'])
def add_manual():
    if request.method == 'POST':
        date = request.form['date']
        merchant = request.form['merchant']
        amount = float(request.form['amount'])
        category = request.form['category']
        payment_type = request.form['payment_type']
        expense = Expense(date=date, merchant=merchant, amount=amount, category=category, payment_type=payment_type)
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_manual.html')

@app.route('/upload_receipt', methods=['GET', 'POST'])
def upload_receipt():
    error = None
    if request.method == 'POST':
        file = request.files.get('receipt')
        if not file or not file.filename:
            error = "Please select a file to upload"
        else:
            # Create uploads folder if it doesn't exist
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            try:
                text = pytesseract.image_to_string(Image.open(filepath))
                print(f"OCR Text: '{text}'")  # Debug: print extracted text
                parsed = parse_receipt(text)
                print(f"Parsed data: {parsed}")  # Debug: print parsed data
                
                if not parsed.get('merchant') or float(parsed.get('amount', 0)) <= 0:
                    error = "Could not extract valid data from receipt. Please try another image or enter manually."
                else:
                    expense = Expense(
                        date=str(parsed.get('date', '')),
                        merchant=str(parsed.get('merchant', 'Unknown')),
                        amount=float(parsed.get('amount', 0.0)),
                        category=str(parsed.get('category', 'Miscellaneous')),
                        payment_type=str(parsed.get('payment_type', 'Cash'))
                    )
                    db.session.add(expense)
                    db.session.commit()
                    return redirect(url_for('index'))
            except TesseractNotFoundError:
                error = "⚠️ Tesseract OCR is not installed on this system. Please use the manual entry form instead."
                print("[WARNING] Tesseract OCR not found. User guided to manual entry.")
            except Exception as e:
                print(f"[ERROR] Receipt processing failed: {str(e)}")
                error = f"Error processing image: {str(e)}. Please try another image or enter it manually."
    return render_template('upload.html', error=error)

@app.route('/add_sms', methods=['GET', 'POST'])
def add_sms():
    if request.method == 'POST':
        sms_text = request.form['sms_text']
        parsed = parse_sms(sms_text)
        expense = Expense(
            date=str(parsed.get('date', '')),
            merchant=str(parsed.get('merchant', 'Unknown')),
            amount=float(parsed.get('amount', 0.0)),
            category=str(parsed.get('category', 'Miscellaneous')),
            payment_type=str(parsed.get('payment_type', 'Cash'))
        )
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_sms.html')

@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/insights')
def insights():
    insights_data = generate_insights()
    return render_template('insights.html', insights=insights_data)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    question = data.get('question', '')
    # build default response
    answer = "Sorry, I don't have an answer for that."
    # if openai available use model
    if openai and openai.api_key:
        # provide some context about expenses
        expenses = Expense.query.all()
        total = sum(e.amount for e in expenses)
        profile = UserProfile.query.first()
        target = profile.monthly_target if profile else None
        system_prompt = (
            "You are an expense tracking assistant. "
            "Answer user queries about their expenses based on available data. "
        )
        user_prompt = f"User question: {question}\nTotal spent: {total:.2f}."
        if target:
            user_prompt += f" Monthly target: {target:.2f}."
        try:
            # Support both legacy `openai.ChatCompletion.create` and the newer
            # `OpenAI` client (client.chat.completions.create) depending on
            # installed `openai` package version.
            ChatCompletion = getattr(openai, 'ChatCompletion', None)
            if ChatCompletion:
                completion = ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=150,
                    temperature=0.5,
                )
                # older clients return dict-like message
                try:
                    answer = completion.choices[0].message['content'].strip()
                except Exception:
                    try:
                        answer = completion.choices[0].text.strip()
                    except Exception:
                        answer = str(completion)
            else:
                OpenAI = getattr(openai, 'OpenAI', None)
                if OpenAI:
                    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY', openai.api_key or None))
                    resp = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        max_tokens=150,
                        temperature=0.5,
                    )
                    try:
                        answer = resp.choices[0].message.content.strip()
                    except Exception:
                        try:
                            answer = resp.choices[0].message['content'].strip()
                        except Exception:
                            answer = str(resp)
                else:
                    answer = "AI client not available"
        except Exception as e:
            answer = f"AI service error: {str(e)}"
    else:
        # fallback simple rules
        q = question.lower()
        if 'total' in q:
            total = sum(e.amount for e in Expense.query.all())
            answer = f"Your total recorded expenses amount to ₹{total:.2f}."
        elif 'category' in q:
            answer = "You can view category breakdown under Analytics."
        elif 'target' in q:
            profile = UserProfile.query.first()
            if profile and profile.monthly_target:
                answer = f"Your monthly expense target is ₹{profile.monthly_target:.2f}."
            else:
                answer = "You have not set a monthly target yet."
    return jsonify({'answer': answer})
@app.route('/visualize')
def visualize():
    return render_template('visualize.html')

@app.route('/api/expenses')
def api_expenses():
    expenses = Expense.query.all()
    return jsonify([e.to_dict() for e in expenses])

def filter_by_date_range(expense_data, start_date, end_date):
    from datetime import datetime
    filtered = []
    for expense in expense_data:
        date_str = expense.get('date') if isinstance(expense, dict) else getattr(expense, 'date', '')
        if not date_str:
            continue
        try:
            expense_date = datetime.strptime(date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            continue
        if start_date <= expense_date.date() <= end_date:
            filtered.append(expense)
    return filtered

@app.route('/api/visualization/<period>')
def get_visualization_data(period):
    # Get all expenses
    expenses = Expense.query.all()

    # Convert to list of dicts
    expense_data = [e.to_dict() for e in expenses]

    # Filter by period or custom range
    filtered_data = []
    now = datetime.now()

    if period == 'custom':
        # custom handling is done in separate endpoint
        filtered_data = expense_data
    else:
        for expense in expense_data:
            date_str = expense.get('date') if isinstance(expense, dict) else getattr(expense, 'date', '')
            if not date_str:
                continue
            try:
                expense_date = datetime.strptime(date_str, '%Y-%m-%d')
            except (ValueError, TypeError):
                continue

            if period == 'daily':
                if expense_date.date() == now.date():
                    filtered_data.append(expense)
            elif period == 'weekly':
                week_start = now - timedelta(days=now.weekday())
                if expense_date >= week_start:
                    filtered_data.append(expense)
            elif period == 'monthly':
                if expense_date.year == now.year and expense_date.month == now.month:
                    filtered_data.append(expense)
            elif period == 'quarterly':
                current_quarter = (now.month - 1) // 3 + 1
                expense_quarter = (expense_date.month - 1) // 3 + 1
                if expense_date.year == now.year and expense_quarter == current_quarter:
                    filtered_data.append(expense)
            elif period == 'semi-annually':
                current_half = 1 if now.month <= 6 else 2
                expense_half = 1 if expense_date.month <= 6 else 2
                if expense_date.year == now.year and expense_half == current_half:
                    filtered_data.append(expense)
            elif period == 'annually':
                if expense_date.year == now.year:
                    filtered_data.append(expense)

    # Group by category for pie chart
    category_totals: dict[str, float] = {}
    for expense in filtered_data:
        cat = str(expense.get('category', 'Miscellaneous'))
        amt = float(expense.get('amount', 0.0))
        category_totals[cat] = category_totals.get(cat, 0.0) + amt

    # Prepare data for charts
    pie_data = {
        'labels': list(category_totals.keys()),
        'data': list(category_totals.values())
    }

    # For bar chart, group by date
    date_totals: dict[str, float] = {}
    for expense in filtered_data:
        date_key = str(expense.get('date', ''))
        amount_val = float(expense.get('amount', 0.0))
        date_totals[date_key] = date_totals.get(date_key, 0.0) + amount_val

    # sort by date for ascending order
    sorted_dates = sorted(date_totals.keys())
    bar_data = {
        'labels': sorted_dates,
        'data': [date_totals[d] for d in sorted_dates]
    }

    return jsonify({
        'pie': pie_data,
        'bar': bar_data,
        'total_expenses': len(filtered_data),
        'total_amount': sum(expense['amount'] for expense in filtered_data)
    })

@app.route('/api/visualization/custom')
def get_custom_visualization():
    from datetime import datetime
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end:
        return jsonify({'error': 'Missing start or end date'}), 400
    try:
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Invalid date format'}), 400
    
    expenses = Expense.query.all()
    expense_data = [e.to_dict() for e in expenses]
    filtered = filter_by_date_range(expense_data, start_date, end_date)

    # compute totals
    category_totals: dict[str, float] = {}
    date_totals: dict[str, float] = {}
    for exp in filtered:
        cat = str(exp.get('category', 'Miscellaneous'))
        amt = float(exp.get('amount', 0.0))
        category_totals[cat] = category_totals.get(cat, 0.0) + amt
        date_key = str(exp.get('date', ''))
        date_totals[date_key] = date_totals.get(date_key, 0.0) + amt

    pie = {'labels': list(category_totals.keys()), 'data': list(category_totals.values())}
    # sort dates for bar
    sorted_dates = sorted(date_totals.keys())
    bar = {'labels': sorted_dates, 'data': [date_totals[d] for d in sorted_dates]}

    return jsonify({
        'pie': pie,
        'bar': bar,
        'total_expenses': len(filtered),
        'total_amount': sum(e['amount'] for e in filtered)
    })

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
    monthly_income = float(app.config.get('MONTHLY_INCOME', 50000))
    if total_spending > monthly_income * 0.8:
        warnings.append(f"You've spent ₹{total_spending:.0f} which is {(total_spending/monthly_income)*100:.1f}% of your monthly income of ₹{monthly_income}.")

    for category, amount in sorted_categories:
        if amount > monthly_income * 0.3:  # More than 30% on one category
            warnings.append(f"You're spending ₹{amount:.0f} on {category}, which is {(amount/monthly_income)*100:.1f}% of your income.")

    # Recommendations
    recommendations: list[str] = []
    high_spending_categories = [cat for cat, amt in sorted_categories if float(amt) > total_spending * 0.2]
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
        date = '2026-03-12'  # Default

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
    print(f"Parsing receipt text: '{text}'")  # Debug print
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
        date = '2026-03-12'  # Default

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
        print(f"Found amount with currency: {amount}")  # Debug
    else:
        amount_match = re.search(r'\b(\d+(?:\.\d{2})?)\b', text)
        if amount_match:
            amount = float(amount_match.group(1))
            print(f"Found amount without currency: {amount}")  # Debug

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

    result = {
        'date': date,
        'merchant': merchant,
        'amount': amount,
        'category': category,
        'payment_type': payment_type
    }
    print(f"Parsed result: {result}")  # Debug print
    return result

def ensure_profile_columns():
    # add needed columns if missing
    inspector = db.inspect(db.engine)
    if 'user_profile' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('user_profile')]
        if 'monthly_target' not in cols:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE user_profile ADD COLUMN monthly_target FLOAT DEFAULT 0.0'))
                    conn.commit()
                print('Added monthly_target column to user_profile')
            except Exception as e:
                print('Failed to add monthly_target column:', e)
        if 'avatar' not in cols:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE user_profile ADD COLUMN avatar VARCHAR(200)'))
                    conn.commit()
                print('Added avatar column to user_profile')
            except Exception as e:
                print('Failed to add avatar column:', e)

# run upgrade early on import inside app context so queries don't fail
with app.app_context():
    db.create_all()
    ensure_profile_columns()

if __name__ == '__main__':
    app.run(debug=True)