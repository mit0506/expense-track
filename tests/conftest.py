import os
import pytest
from app import create_app
from app.models import db as _db, UserProfile
from werkzeug.security import generate_password_hash

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['SECRET_KEY'] = 'test-secret-key'


@pytest.fixture(scope='session')
def app():
    """Create a Flask app configured for testing."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
    })
    # Disable rate limiter in tests
    from app import limiter
    limiter.enabled = False
    yield app


@pytest.fixture(autouse=True)
def _reset_db(app):
    """Recreate all tables before each test for full isolation."""
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield
        _db.session.remove()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app):
    """Test client with a logged-in user."""
    with app.app_context():
        user = UserProfile(
            username='testuser',
            password_hash=generate_password_hash('password123'),
            monthly_income=50000,
            monthly_target=30000,
        )
        _db.session.add(user)
        _db.session.commit()

        with app.test_client() as c:
            c.post('/login', data={'username': 'testuser', 'password': 'password123'})
            yield c
