import os
import re
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from .models import db, Expense, UserProfile
from .utils import parse_sms, parse_receipt, generate_insights, parse_sms
import pytesseract
from PIL import Image
from pytesseract import TesseractNotFoundError

main_bp = Blueprint('main', __name__)

# optional AI chatbot integration - handled at module level
try:
    import openai  # type: ignore[import]
    # openai.api_key is set during app creation in __init__.py
except ImportError:
    openai = None

@main_bp.route('/')
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

@main_bp.context_processor
def inject_global_data():
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile(name='User', monthly_income=current_app.config.get('MONTHLY_INCOME', 0))
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

@main_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    # allow user to set name, income, monthly expense target, and avatar
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile(
            name='User',
            monthly_income=current_app.config.get('MONTHLY_INCOME', 0),
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
            avatar_dir = os.path.join(str(current_app.static_folder), 'avatars')
            if not os.path.exists(avatar_dir):
                os.makedirs(avatar_dir)
            filepath = os.path.join(avatar_dir, filename)
            file.save(filepath)
            profile.avatar = filename
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('profile.html', profile=profile)


@main_bp.route('/add_manual', methods=['GET', 'POST'])
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
        return redirect(url_for('main.index'))
    return render_template('add_manual.html')

@main_bp.route('/upload_receipt', methods=['GET', 'POST'])
def upload_receipt():
    error = None
    if request.method == 'POST':
        file = request.files.get('receipt')
        if not file or not file.filename:
            error = "Please select a file to upload"
        else:
            # Create uploads folder if it doesn't exist
            if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
                os.makedirs(current_app.config['UPLOAD_FOLDER'])
            
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            try:
                text = pytesseract.image_to_string(Image.open(filepath))
                parsed = parse_receipt(text)
                
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
                    return redirect(url_for('main.index'))
            except TesseractNotFoundError:
                error = "⚠️ Tesseract OCR is not installed on this system. Please use the manual entry form instead."
            except Exception as e:
                error = f"Error processing image: {str(e)}. Please try another image or enter it manually."
    return render_template('upload.html', error=error)

@main_bp.route('/add_sms', methods=['GET', 'POST'])
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
        return redirect(url_for('main.index'))
    return render_template('add_sms.html')

@main_bp.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('main.index'))

@main_bp.route('/insights')
def insights():
    insights_data = generate_insights()
    return render_template('insights.html', insights=insights_data)

@main_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    question = data.get('question', '')
    answer = "Sorry, I don't have an answer for that."
    
    # if openai available use model
    if openai and openai.api_key:
        expenses = Expense.query.all()
        total = sum(e.amount for e in expenses)
        profile = UserProfile.query.first()
        target = profile.monthly_target if profile else None
        system_prompt = "You are an expense tracking assistant. Answer user queries based on available data."
        user_prompt = f"User question: {question}\nTotal spent: {total:.2f}."
        if target:
            user_prompt += f" Monthly target: {target:.2f}."
        try:
            ChatCompletion = getattr(openai, 'ChatCompletion', None)
            if ChatCompletion:
                completion = ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    max_tokens=150, temperature=0.5
                )
                answer = completion.choices[0].message['content'].strip()
            else:
                OpenAI = getattr(openai, 'OpenAI', None)
                if OpenAI:
                    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY', openai.api_key or None))
                    resp = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                        max_tokens=150, temperature=0.5
                    )
                    answer = resp.choices[0].message.content.strip()
        except Exception as e:
            answer = f"AI service error: {str(e)}"
    else:
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

@main_bp.route('/visualize')
def visualize():
    return render_template('visualize.html')

@main_bp.route('/api/expenses')
def api_expenses():
    expenses = Expense.query.all()
    return jsonify([e.to_dict() for e in expenses])

@main_bp.route('/api/visualization/<period>')
def get_visualization_data(period):
    expenses = Expense.query.all()
    expense_data = [e.to_dict() for e in expenses]
    filtered_data = []
    now = datetime.now()

    for expense in expense_data:
        date_str = str(expense.get('date', ''))
        if not date_str: continue
        try:
            expense_date = datetime.strptime(date_str, '%Y-%m-%d')
        except: continue

        if period == 'daily' and expense_date.date() == now.date(): filtered_data.append(expense)
        elif period == 'weekly' and expense_date >= now - timedelta(days=now.weekday()): filtered_data.append(expense)
        elif period == 'monthly' and expense_date.year == now.year and expense_date.month == now.month: filtered_data.append(expense)
        elif period == 'quarterly':
            if expense_date.year == now.year and ((now.month-1)//3+1 == (expense_date.month-1)//3+1): filtered_data.append(expense)
        elif period == 'annually' and expense_date.year == now.year: filtered_data.append(expense)

    category_totals: dict[str, float] = {}
    for expense in filtered_data:
        cat = str(expense.get('category', 'Miscellaneous'))
        amt = float(expense.get('amount', 0.0))
        category_totals[cat] = category_totals.get(cat, 0.0) + amt

    pie_data = {'labels': list(category_totals.keys()), 'data': list(category_totals.values())}
    date_totals: dict[str, float] = {}
    for expense in filtered_data:
        date_key = str(expense.get('date', ''))
        amount_val = float(expense.get('amount', 0.0))
        date_totals[date_key] = date_totals.get(date_key, 0.0) + amount_val

    sorted_dates = sorted(date_totals.keys())
    bar_data = {'labels': sorted_dates, 'data': [date_totals[d] for d in sorted_dates]}

    return jsonify({
        'pie': pie_data, 'bar': bar_data,
        'total_expenses': len(filtered_data),
        'total_amount': sum(expense['amount'] for expense in filtered_data)
    })

@main_bp.route('/api/visualization/custom')
def get_custom_visualization():
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end: return jsonify({'error': 'Missing dates'}), 400
    try:
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
    except: return jsonify({'error': 'Invalid format'}), 400
    
    expenses = Expense.query.all()
    filtered = []
    for exp in expenses:
        try:
            ed = datetime.strptime(exp.date, '%Y-%m-%d').date()
            if start_date <= ed <= end_date: filtered.append(exp.to_dict())
        except: continue

    category_totals: dict[str, float] = {}
    date_totals: dict[str, float] = {}
    for exp in filtered:
        cat = str(exp.get('category', 'Miscellaneous'))
        amt = float(exp.get('amount', 0.0))
        category_totals[cat] = category_totals.get(cat, 0.0) + amt
        dk = str(exp.get('date', ''))
        date_totals[dk] = date_totals.get(dk, 0.0) + amt

    return jsonify({
        'pie': {'labels': list(category_totals.keys()), 'data': list(category_totals.values())},
        'bar': {'labels': sorted(date_totals.keys()), 'data': [date_totals[d] for d in sorted(date_totals.keys())]},
        'total_expenses': len(filtered),
        'total_amount': sum(e['amount'] for e in filtered)
    })
