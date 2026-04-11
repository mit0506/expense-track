import logging
from datetime import datetime, timedelta
from flask import request, jsonify
from flask_login import login_required, current_user
from app.models import db, Expense
from app.routes import main_bp
from app.utils import generate_insights
from app import limiter

try:
    import openai  # type: ignore[import]
except ImportError:
    openai = None

logger = logging.getLogger(__name__)

VALID_PERIODS = {'daily', 'weekly', 'monthly', 'quarterly', 'annually'}


@main_bp.route('/insights')
@login_required
def insights():
    from flask import render_template
    return render_template('insights.html', insights=generate_insights(current_user.id))


@main_bp.route('/visualize')
@login_required
def visualize():
    from flask import render_template
    return render_template('visualize.html')


@main_bp.route('/api/expenses')
@login_required
@limiter.limit("60 per minute")
def api_expenses():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 200)
    pagination = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        'expenses': [e.to_dict() for e in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
    })


def _filter_expenses_by_period(user_id, period):
    now = datetime.now()
    expenses = Expense.query.filter_by(user_id=user_id).all()
    filtered = []
    for e in expenses:
        if not e.date:
            continue
        try:
            ed = datetime.strptime(e.date, '%Y-%m-%d')
        except (ValueError, TypeError):
            continue

        match = False
        if period == 'daily':
            match = ed.date() == now.date()
        elif period == 'weekly':
            match = ed >= now - timedelta(days=now.weekday())
        elif period == 'monthly':
            match = ed.year == now.year and ed.month == now.month
        elif period == 'quarterly':
            match = ed.year == now.year and ((now.month - 1) // 3 == (ed.month - 1) // 3)
        elif period == 'annually':
            match = ed.year == now.year

        if match:
            filtered.append(e.to_dict())
    return filtered


def _build_visualization_response(filtered):
    cat_totals: dict[str, float] = {}
    date_totals: dict[str, float] = {}
    for e in filtered:
        cat_totals[e['category']] = cat_totals.get(e['category'], 0) + float(e['amount'])
        date_totals[e['date']] = date_totals.get(e['date'], 0) + float(e['amount'])

    sd = sorted(date_totals.keys())
    return {
        'pie': {'labels': list(cat_totals.keys()), 'data': list(cat_totals.values())},
        'bar': {'labels': sd, 'data': [date_totals[d] for d in sd]},
        'total_expenses': len(filtered),
        'total_amount': sum(e['amount'] for e in filtered)
    }


@main_bp.route('/api/visualization/<period>')
@login_required
@limiter.limit("30 per minute")
def get_visualization_data(period):
    if period not in VALID_PERIODS:
        return jsonify({'error': 'Invalid period'}), 400
    filtered = _filter_expenses_by_period(current_user.id, period)
    return jsonify(_build_visualization_response(filtered))


@main_bp.route('/api/visualization/custom')
@login_required
@limiter.limit("30 per minute")
def get_custom_visualization():
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end:
        return jsonify({'error': 'Missing dates'}), 400
    try:
        sd = datetime.strptime(start, '%Y-%m-%d').date()
        ed = datetime.strptime(end, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    filtered = []
    for exp in Expense.query.filter_by(user_id=current_user.id).all():
        try:
            exp_date = datetime.strptime(exp.date, '%Y-%m-%d').date()
            if sd <= exp_date <= ed:
                filtered.append(exp.to_dict())
        except (ValueError, TypeError):
            continue

    return jsonify(_build_visualization_response(filtered))


@main_bp.route('/chat', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def chat():
    data = request.get_json(silent=True) or {}
    q = str(data.get('question', ''))[:500].lower()
    if not q.strip():
        return jsonify({'error': 'Question is required.'}), 400

    if openai and getattr(openai, 'api_key', None):
        total = (
            db.session.query(db.func.sum(Expense.amount))
            .filter_by(user_id=current_user.id)
            .scalar()
        ) or 0
        user_prompt = f"User question: {q}\nTotal spent: {float(total):.2f}. Target: {current_user.monthly_target}"
        try:
            ChatCompletion = getattr(openai, 'ChatCompletion', None)
            if ChatCompletion:
                res = ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": user_prompt}])
                return jsonify({'answer': res.choices[0].message['content'].strip()})
            else:
                client = getattr(openai, 'OpenAI', None)(api_key=openai.api_key)
                msgs = [{"role": "user", "content": user_prompt}]
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=msgs)
                return jsonify({'answer': res.choices[0].message.content.strip()})
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            return jsonify({'answer': "AI service is temporarily unavailable. Please try again."})

    if 'total' in q:
        total = (
            db.session.query(db.func.sum(Expense.amount))
            .filter_by(user_id=current_user.id)
            .scalar()
        ) or 0
        return jsonify({'answer': f"Your total is ₹{float(total):.2f}."})
    elif 'target' in q:
        return jsonify({'answer': f"Your target is ₹{current_user.monthly_target}."})
    return jsonify({'answer': "No AI config. Try asking 'total' or 'target'."})
