import os
import logging
from flask import Flask, jsonify, render_template, request, redirect, flash
from app.models import db, UserProfile
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_login import LoginManager

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

login_manager = LoginManager()
login_manager.login_view = 'main.login'

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])
migrate = Migrate()


def create_app():
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        if os.environ.get('FLASK_ENV') == 'production':
            raise RuntimeError("SECRET_KEY environment variable must be set in production")
        secret_key = 'dev_default_key_123'
    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///expenses.db')
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MONTHLY_INCOME'] = 50000

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    @login_manager.user_loader
    def load_user(user_id):
        return UserProfile.query.get(int(user_id))

    # optional AI chatbot integration
    try:
        import openai  # type: ignore[import]
        openai.api_key = os.environ.get('OPENAI_API_KEY', '')
    except ImportError:
        pass

    # Try to set Tesseract path if it exists in common Windows locations
    try:
        import pytesseract
        if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
            setattr(pytesseract, 'pytesseract_cmd', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        elif os.path.exists(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
            setattr(pytesseract, 'pytesseract_cmd', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe')
    except ImportError:
        pass

    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(429)
    def rate_limited(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        flash('Too many requests. Please slow down.')
        return redirect(request.referrer or '/')

    @app.errorhandler(500)
    def server_error(e):
        logger.error("Internal server error: %s", e)
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500

    with app.app_context():
        db.create_all()

    return app
