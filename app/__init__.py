import os
from flask import Flask
from .models import db, UserProfile
from sqlalchemy import text
import pytesseract

def create_app():
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MONTHLY_INCOME'] = 50000  # Default monthly income

    # Database initialization
    db.init_app(app)

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
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # Database setup and migrations
    with app.app_context():
        db.create_all()
        ensure_profile_columns(db)

    return app

def ensure_profile_columns(db):
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
