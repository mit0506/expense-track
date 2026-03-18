import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, UserProfile

app = create_app()

with app.app_context():
    db.create_all()
    print('Tables successfully initialized.')
    profiles = UserProfile.query.all()
    print(f'Total profiles in database: {len(profiles)}')
