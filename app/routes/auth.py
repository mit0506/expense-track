import os
import logging
from flask import render_template, request, redirect, url_for, current_app, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app.models import db, UserProfile, CategoryBudget
from app.constants import EXPENSE_CATEGORIES, ALLOWED_AVATAR_EXTENSIONS
from app.validators import validate_username, validate_password, sanitize_string, validate_amount
from app.routes import main_bp
from app import limiter

logger = logging.getLogger(__name__)


def _allowed_avatar(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


@main_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        raw_username = request.form.get('username', '')
        password = request.form.get('password', '')

        username, err = validate_username(raw_username)
        if err:
            flash(err)
            return redirect(url_for('main.register'))
        password, err = validate_password(password)
        if err:
            flash(err)
            return redirect(url_for('main.register'))

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
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
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


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = sanitize_string(request.form.get('name', current_user.name), max_length=100)
        try:
            income = float(request.form.get('monthly_income', current_user.monthly_income))
            target = float(request.form.get('monthly_target', current_user.monthly_target))
            if 0 <= income <= 99_999_999:
                current_user.monthly_income = income
            if 0 <= target <= 99_999_999:
                current_user.monthly_target = target
        except (ValueError, TypeError):
            logger.warning("Invalid income/target values submitted by user %s", current_user.id)

        if request.form.get('delete_avatar'):
            if current_user.avatar:
                old_avatar_path = os.path.join(str(current_app.static_folder), 'avatars', current_user.avatar)
                if os.path.exists(old_avatar_path):
                    try:
                        os.remove(old_avatar_path)
                    except OSError:
                        logger.warning("Failed to delete avatar file: %s", old_avatar_path)
                current_user.avatar = None
        else:
            file = request.files.get('avatar')
            if file and file.filename:
                if not _allowed_avatar(file.filename):
                    flash('Invalid file type. Allowed: jpg, jpeg, png, gif, webp.')
                else:
                    filename = secure_filename(file.filename)
                    if filename:
                        avatar_dir = os.path.join(str(current_app.static_folder), 'avatars')
                        if not os.path.exists(avatar_dir):
                            os.makedirs(avatar_dir)
                        filepath = os.path.join(avatar_dir, filename)
                        file.save(filepath)
                        current_user.avatar = filename

        for cat in EXPENSE_CATEGORIES:
            cat_budget = request.form.get(f'budget_{cat}')
            if cat_budget is not None and cat_budget != '':
                try:
                    cval = float(cat_budget)
                    if cval < 0:
                        continue
                    cb = CategoryBudget.query.filter_by(user_id=current_user.id, category=cat).first()
                    if not cb:
                        cb = CategoryBudget(user_id=current_user.id, category=cat, amount=cval)
                        db.session.add(cb)
                    else:
                        cb.amount = cval
                except (ValueError, TypeError):
                    logger.warning("Invalid budget value for category %s by user %s", cat, current_user.id)

        db.session.commit()
        return redirect(url_for('main.index'))

    category_budgets = {b.category: float(b.amount) for b in CategoryBudget.query.filter_by(user_id=current_user.id).all()}
    return render_template('profile.html', profile=current_user, category_budgets=category_budgets)
