import os
import csv
import logging
from io import StringIO
from datetime import datetime
from flask import render_template, request, redirect, url_for, current_app, flash, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Expense, UserProfile, CategoryBudget, BillSplit
from app.utils import parse_sms, parse_receipt
from app.constants import EXPENSE_CATEGORIES, MAX_EXPENSE_AMOUNT
from app.routes import main_bp

try:
    import pytesseract
    from PIL import Image
    from pytesseract import TesseractNotFoundError
except ImportError:
    pytesseract = None
    TesseractNotFoundError = Exception

logger = logging.getLogger(__name__)

ALLOWED_RECEIPT_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'}


def _validate_amount(raw_value):
    try:
        amount = float(raw_value)
    except (ValueError, TypeError):
        return None
    if amount <= 0 or amount > MAX_EXPENSE_AMOUNT:
        return None
    return amount


def _validate_category(category):
    if category in EXPENSE_CATEGORIES:
        return category
    return 'Miscellaneous'


def _create_expense_from_parsed(parsed):
    amount = _validate_amount(parsed.get('amount', 0))
    if amount is None:
        amount = 0.0
    return Expense(
        user_id=current_user.id,
        date=str(parsed.get('date', '')),
        merchant=str(parsed.get('merchant', 'Unknown'))[:100],
        amount=amount,
        category=_validate_category(str(parsed.get('category', 'Miscellaneous'))),
        payment_type=str(parsed.get('payment_type', 'Cash'))
    )


@main_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    pagination = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc(), Expense.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    expenses = pagination.items

    today = datetime.today()
    prefix = today.strftime('%Y-%m')

    cat_spending: dict[str, float] = {}
    total_monthly = float(
        db.session.query(db.func.sum(Expense.amount))
        .filter(Expense.user_id == current_user.id, Expense.date.like(f'{prefix}%'))
        .scalar() or 0
    )

    # Category breakdown for current month
    cat_rows = (
        db.session.query(Expense.category, db.func.sum(Expense.amount))
        .filter(Expense.user_id == current_user.id, Expense.date.like(f'{prefix}%'))
        .group_by(Expense.category)
        .all()
    )
    cat_spending = {row[0]: float(row[1]) for row in cat_rows}

    cat_budgets_objs = CategoryBudget.query.filter_by(user_id=current_user.id).all()
    cat_budgets = {b.category: float(b.amount) for b in cat_budgets_objs if b.amount and float(b.amount) > 0}

    target_exceeded = bool(current_user.monthly_target and total_monthly > float(current_user.monthly_target))
    return render_template(
        'index.html',
        expenses=expenses,
        pagination=pagination,
        target_exceeded=target_exceeded,
        monthly_total=total_monthly,
        cat_spending=cat_spending,
        cat_budgets=cat_budgets,
    )


@main_bp.route('/add_manual', methods=['GET', 'POST'])
@login_required
def add_manual():
    if request.method == 'POST':
        amount = _validate_amount(request.form.get('amount'))
        if amount is None:
            flash('Invalid amount. Must be between 0.01 and 9,999,999.99.')
            return redirect(url_for('main.add_manual'))

        expense = Expense(
            user_id=current_user.id,
            date=request.form.get('date', ''),
            merchant=request.form.get('merchant', '')[:100],
            amount=amount,
            category=_validate_category(request.form.get('category', 'Miscellaneous')),
            payment_type=request.form.get('payment_type', 'Cash'),
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
        amount = _validate_amount(request.form.get('amount', expense.amount))
        if amount is None:
            flash('Invalid amount.')
            return redirect(url_for('main.edit_expense', expense_id=expense_id))

        expense.date = request.form.get('date', expense.date)
        expense.merchant = request.form.get('merchant', expense.merchant)[:100]
        expense.amount = amount
        expense.category = _validate_category(request.form.get('category', expense.category))
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


@main_bp.route('/upload_receipt', methods=['GET', 'POST'])
@login_required
def upload_receipt():
    error = None
    if request.method == 'POST':
        file = request.files.get('receipt')
        if not file or not file.filename:
            error = "Please select a file to upload"
        else:
            filename = secure_filename(file.filename)
            if not filename or not ('.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_RECEIPT_EXTENSIONS):
                error = "Invalid file type. Please upload an image file."
            else:
                upload_folder = current_app.config['UPLOAD_FOLDER']
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                try:
                    if pytesseract is None:
                        error = "Tesseract OCR is not installed. Use manual entry."
                    else:
                        text = pytesseract.image_to_string(Image.open(filepath))
                        parsed = parse_receipt(text)
                        if not parsed.get('merchant') or float(parsed.get('amount', 0)) <= 0:
                            error = "Could not extract valid data. Try another image or entering manually."
                        else:
                            expense = _create_expense_from_parsed(parsed)
                            db.session.add(expense)
                            db.session.commit()
                            return redirect(url_for('main.index'))
                except TesseractNotFoundError:
                    error = "Tesseract OCR is not installed. Use manual entry."
                except (OSError, ValueError) as e:
                    logger.error("Error processing receipt: %s", e)
                    error = "Error processing image. Please try again or use manual entry."
    return render_template('upload.html', error=error)


@main_bp.route('/add_sms', methods=['GET', 'POST'])
@login_required
def add_sms():
    if request.method == 'POST':
        sms_text = request.form.get('sms_text', '')
        if not sms_text.strip():
            flash('Please enter SMS text.')
            return redirect(url_for('main.add_sms'))
        parsed = parse_sms(sms_text)
        expense = _create_expense_from_parsed(parsed)
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('add_sms.html')


@main_bp.route('/split/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def split_expense(expense_id):
    expense = Expense.query.filter(
        (Expense.id == expense_id) & (Expense.user_id == current_user.id)
    ).first_or_404()

    if request.method == 'POST':
        try:
            debtor_id = int(request.form.get('debtor_id', 0))
            split_amount = float(request.form.get('amount', 0))
        except (ValueError, TypeError):
            flash("Invalid input.")
            return redirect(url_for('main.split_expense', expense_id=expense_id))

        debtor = UserProfile.query.get(debtor_id)
        if not debtor or debtor.id == current_user.id:
            flash("Invalid debtor selected.")
            return redirect(url_for('main.split_expense', expense_id=expense_id))

        if split_amount <= 0 or split_amount > float(expense.amount):
            flash("Split amount must be between 0 and the total transaction amount.")
            return redirect(url_for('main.split_expense', expense_id=expense_id))

        new_split = BillSplit(
            expense_id=expense.id,
            payer_id=current_user.id,
            debtor_id=debtor_id,
            amount=split_amount
        )
        db.session.add(new_split)
        db.session.commit()
        flash(f"Split registered successfully! User {debtor.username} now owes ₹{split_amount}.")
        return redirect(url_for('main.index'))

    other_users = UserProfile.query.filter(UserProfile.id != current_user.id).all()
    return render_template('split_expense.html', expense=expense, users=other_users)


@main_bp.route('/settle/<int:split_id>', methods=['POST'])
@login_required
def settle_split(split_id):
    split = BillSplit.query.filter(
        (BillSplit.id == split_id) & ((BillSplit.payer_id == current_user.id) | (BillSplit.debtor_id == current_user.id))
    ).first_or_404()
    split.settled = True
    db.session.commit()
    return redirect(url_for('main.index'))


@main_bp.route('/export_csv')
@login_required
def export_csv():
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Date', 'Merchant', 'Amount', 'Category', 'Payment_Type'])
    for e in expenses:
        cw.writerow([e.id, e.date, e.merchant, float(e.amount) if e.amount else 0, e.category, e.payment_type])
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=expenses_export.csv"}
    )
