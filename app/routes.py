import os
import re
import csv
from io import StringIO
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, flash, Response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, Expense, UserProfile, CategoryBudget, Subscription
from app.utils import parse_sms, parse_receipt, generate_insights
import pytesseract
from PIL import Image
from pytesseract import TesseractNotFoundError

main_bp = Blueprint('main', __name__)

try:
    import openai  # type: ignore[import]
except ImportError:
    openai = None

def process_subscriptions(user_id):
    today = datetime.today().date()
    subs = Subscription.query.filter_by(user_id=user_id, auto_log=True).all()
    for sub in subs:
        if sub.next_billing_date:
            try:
                next_date = datetime.strptime(sub.next_billing_date, '%Y-%m-%d').date()
                while next_date <= today:
                    new_exp = Expense(
                        user_id=user_id,
                        date=next_date.strftime('%Y-%m-%d'),
                        merchant=sub.merchant,
                        amount=sub.amount,
                        category=sub.category,
                        payment_type='Auto (Sub)'
                    )
                    db.session.add(new_exp)
                    
                    if sub.billing_cycle == 'monthly':
                        month = next_date.month % 12 + 1
                        year = next_date.year + (next_date.month // 12)
                        
                        # handle end of month clamping (lazy approach for 28/30/31 days)
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
            except Exception:
                pass
    db.session.commit()

@main_bp.context_processor
def inject_global_data():
    if not current_user.is_authenticated:
        return {'monthly_total': 0.0}
    
    # Process due subscriptions right before building context!
    process_subscriptions(current_user.id)
    
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    today = datetime.today()
    prefix = today.strftime('%Y-%m')
    total_spending = sum(float(e.amount or 0) for e in expenses if e.date and str(e.date).startswith(prefix))
    return {'monthly_total': total_spending}

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if UserProfile.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('main.register'))
        
        user = UserProfile(
            username=username, 
            password_hash=generate_password_hash(password),
            monthly_income=current_app.config.get('MONTHLY_INCOME', 50000)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('main.index'))
    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = UserProfile.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main_bp.route('/')
@login_required
def index():
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc(), Expense.id.desc()).all()
    today = datetime.today()
    prefix = today.strftime('%Y-%m')
    
    cat_spending = {}
    total_monthly = 0.0
    for e in expenses:
        if str(e.date).startswith(prefix):
            c_amt = float(e.amount or 0)
            total_monthly += c_amt
            cat_spending[e.category] = cat_spending.get(e.category, 0.0) + c_amt
            
    cat_budgets_objs = CategoryBudget.query.filter_by(user_id=current_user.id).all()
    cat_budgets = {b.category: b.amount for b in cat_budgets_objs if b.amount > 0}

    target_exceeded = bool(current_user.monthly_target and total_monthly > float(current_user.monthly_target))
    return render_template('index.html', expenses=expenses, target_exceeded=target_exceeded, monthly_total=total_monthly, cat_spending=cat_spending, cat_budgets=cat_budgets)

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name)
        try:
            current_user.monthly_income = float(request.form.get('monthly_income', current_user.monthly_income))
            current_user.monthly_target = float(request.form.get('monthly_target', current_user.monthly_target))
        except ValueError:
            pass

        if request.form.get('delete_avatar'):
            if current_user.avatar:
                old_avatar_path = os.path.join(str(current_app.static_folder), 'avatars', current_user.avatar)
                if os.path.exists(old_avatar_path):
                    try:
                        os.remove(old_avatar_path)
                    except Exception:
                        pass
                current_user.avatar = None
        else:
            file = request.files.get('avatar')
            if file and file.filename:
                filename = file.filename
                avatar_dir = os.path.join(str(current_app.static_folder), 'avatars')
                if not os.path.exists(avatar_dir):
                    os.makedirs(avatar_dir)
                filepath = os.path.join(avatar_dir, filename)
                file.save(filepath)
                current_user.avatar = filename
                
        # Category Budgets
        categories = ['Food', 'Transport', 'Shopping', 'Entertainment', 'Health', 'Rent', 'Utilities', 'Miscellaneous']
        for cat in categories:
            cat_budget = request.form.get(f'budget_{cat}')
            if cat_budget is not None and cat_budget != '':
                try:
                    cval = float(cat_budget)
                    cb = CategoryBudget.query.filter_by(user_id=current_user.id, category=cat).first()
                    if not cb:
                        cb = CategoryBudget(user_id=current_user.id, category=cat, amount=cval)
                        db.session.add(cb)
                    else:
                        cb.amount = cval
                except Exception:
                    pass

        db.session.commit()
        return redirect(url_for('main.index'))
        
    category_budgets = {b.category: b.amount for b in CategoryBudget.query.filter_by(user_id=current_user.id).all()}
    return render_template('profile.html', profile=current_user, category_budgets=category_budgets)

@main_bp.route('/add_manual', methods=['GET', 'POST'])
@login_required
def add_manual():
    if request.method == 'POST':
        expense = Expense(
            user_id=current_user.id,
            date=request.form['date'],
            merchant=request.form['merchant'],
            amount=float(request.form['amount']),
            category=request.form['category'],
            payment_type=request.form['payment_type']
        )
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('add_manual.html')

@main_bp.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        expense.date = request.form.get('date', expense.date)
        expense.merchant = request.form.get('merchant', expense.merchant)
        expense.amount = float(request.form.get('amount', expense.amount))
        expense.category = request.form.get('category', expense.category)
        expense.payment_type = request.form.get('payment_type', expense.payment_type)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('edit_manual.html', expense=expense)

@main_bp.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('main.index'))

@main_bp.route('/subscriptions', methods=['GET', 'POST'])
@login_required
def subscriptions():
    if request.method == 'POST':
        merchant = request.form.get('merchant')
        amount = float(request.form.get('amount'))
        category = request.form.get('category')
        billing_cycle = request.form.get('billing_cycle')
        next_billing_date = request.form.get('next_billing_date')
        
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

@main_bp.route('/export_csv')
@login_required
def export_csv():
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Date', 'Merchant', 'Amount', 'Category', 'Payment_Type'])
    for e in expenses:
        cw.writerow([e.id, e.date, e.merchant, e.amount, e.category, e.payment_type])
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=expenses_export.csv"}
    )

@main_bp.route('/upload_receipt', methods=['GET', 'POST'])
@login_required
def upload_receipt():
    error = None
    if request.method == 'POST':
        file = request.files.get('receipt')
        if not file or not file.filename:
            error = "Please select a file to upload"
        else:
            if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
                os.makedirs(current_app.config['UPLOAD_FOLDER'])
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            try:
                text = pytesseract.image_to_string(Image.open(filepath))
                parsed = parse_receipt(text)
                if not parsed.get('merchant') or float(parsed.get('amount', 0)) <= 0:
                    error = "Could not extract valid data. Try another image or entering manually."
                else:
                    expense = Expense(
                        user_id=current_user.id,
                        date=str(parsed.get('date', '')),
                        merchant=str(parsed.get('merchant', 'Unknown')),
                        amount=float(parsed.get('amount', 0.0)),
                        category=str(parsed.get('category', 'Miscellaneous')),
                        payment_type=str(parsed.get('payment_type', 'Cash'))
                    )
                    db.session.add(expense)
                    db.session.commit()
                    return redirect(url_for('main.index'))
            except TesseractNotFoundError:
                error = "Tesseract OCR is not installed. Use manual entry."
            except Exception as e:
                error = f"Error processing image: {str(e)}."
    return render_template('upload.html', error=error)

@main_bp.route('/add_sms', methods=['GET', 'POST'])
@login_required
def add_sms():
    if request.method == 'POST':
        parsed = parse_sms(request.form['sms_text'])
        expense = Expense(
            user_id=current_user.id,
            date=str(parsed.get('date', '')),
            merchant=str(parsed.get('merchant', 'Unknown')),
            amount=float(parsed.get('amount', 0.0)),
            category=str(parsed.get('category', 'Miscellaneous')),
            payment_type=str(parsed.get('payment_type', 'Cash'))
        )
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('add_sms.html')

@main_bp.route('/insights')
@login_required
def insights():
    return render_template('insights.html', insights=generate_insights(current_user.id))

@main_bp.route('/visualize')
@login_required
def visualize():
    return render_template('visualize.html')

@main_bp.route('/api/expenses')
@login_required
def api_expenses():
    return jsonify([e.to_dict() for e in Expense.query.filter_by(user_id=current_user.id).all()])

@main_bp.route('/api/visualization/<period>')
@login_required
def get_visualization_data(period):
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    filtered = []
    now = datetime.now()
    for e in [x.to_dict() for x in expenses]:
        if not e.get('date'): continue
        try: ed = datetime.strptime(e['date'], '%Y-%m-%d')
        except: continue
        
        if period == 'daily' and ed.date() == now.date(): filtered.append(e)
        elif period == 'weekly' and ed >= now - timedelta(days=now.weekday()): filtered.append(e)
        elif period == 'monthly' and ed.year == now.year and ed.month == now.month: filtered.append(e)
        elif period == 'quarterly' and ed.year == now.year and ((now.month-1)//3 == (ed.month-1)//3): filtered.append(e)
        elif period == 'annually' and ed.year == now.year: filtered.append(e)

    cat_totals = {}
    date_totals = {}
    for e in filtered:
        cat_totals[e['category']] = cat_totals.get(e['category'], 0) + float(e['amount'])
        date_totals[e['date']] = date_totals.get(e['date'], 0) + float(e['amount'])

    sd = sorted(date_totals.keys())
    return jsonify({
        'pie': {'labels': list(cat_totals.keys()), 'data': list(cat_totals.values())},
        'bar': {'labels': sd, 'data': [date_totals[d] for d in sd]},
        'total_expenses': len(filtered),
        'total_amount': sum(e['amount'] for e in filtered)
    })

@main_bp.route('/api/visualization/custom')
@login_required
def get_custom_visualization():
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end: return jsonify({'error': 'Missing dates'}), 400
    try:
        sd = datetime.strptime(start, '%Y-%m-%d').date()
        ed = datetime.strptime(end, '%Y-%m-%d').date()
    except: return jsonify({'error': 'Invalid format'}), 400
    
    filtered = []
    for exp in Expense.query.filter_by(user_id=current_user.id).all():
        try:
            if sd <= datetime.strptime(exp.date, '%Y-%m-%d').date() <= ed:
                filtered.append(exp.to_dict())
        except: pass

    cat_totals = {}
    date_totals = {}
    for e in filtered:
        cat_totals[e['category']] = cat_totals.get(e['category'], 0) + float(e['amount'])
        date_totals[e['date']] = date_totals.get(e['date'], 0) + float(e['amount'])

    skeys = sorted(date_totals.keys())
    return jsonify({
        'pie': {'labels': list(cat_totals.keys()), 'data': list(cat_totals.values())},
        'bar': {'labels': skeys, 'data': [date_totals[d] for d in skeys]},
        'total_expenses': len(filtered),
        'total_amount': sum(e['amount'] for e in filtered)
    })

@main_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json() or {}
    q = data.get('question', '').lower()
    
    if openai and openai.api_key:
        total = sum(e.amount for e in Expense.query.filter_by(user_id=current_user.id).all())
        user_prompt = f"User question: {q}\nTotal spent: {total:.2f}. Target: {current_user.monthly_target}"
        try:
            # Simple wrapper adaptation for openai 0.28 vs >=1.0
            ChatCompletion = getattr(openai, 'ChatCompletion', None)
            if ChatCompletion:
                res = ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": user_prompt}])
                return jsonify({'answer': res.choices[0].message['content'].strip()})
            else:
                client = getattr(openai, 'OpenAI', None)(api_key=openai.api_key)
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": user_prompt}])
                return jsonify({'answer': res.choices[0].message.content.strip()})
        except Exception as e:
            return jsonify({'answer': f"AI error: {str(e)}"})
            
    if 'total' in q:
        total = sum(e.amount for e in Expense.query.filter_by(user_id=current_user.id).all())
        return jsonify({'answer': f"Your total is ₹{total:.2f}."})
    elif 'target' in q:
        return jsonify({'answer': f"Your target is ₹{current_user.monthly_target}."})
    return jsonify({'answer': "No AI config. Try asking 'total' or 'target'."})
