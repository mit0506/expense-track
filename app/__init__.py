import os
from flask import Flask
from app.models import db, UserProfile
from sqlalchemy import text
import pytesseract
from dotenv import load_dotenv
from flask_login import LoginManager

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = 'main.login'

def create_app():
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_default_key_123')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///expenses.db')
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MONTHLY_INCOME'] = 50000  # Default monthly income

    # Database and Login initialization
    db.init_app(app)
    login_manager.init_app(app)

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
        if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
            setattr(pytesseract, 'pytesseract_cmd', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        elif os.path.exists(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
            setattr(pytesseract, 'pytesseract_cmd', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe')
    except Exception:
        pass

    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Database setup
    with app.app_context():
        db.create_all()

    return app
