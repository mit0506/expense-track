from app.models import UserProfile


def test_register_success(client):
    resp = client.post('/register', data={
        'username': 'newuser',
        'password': 'securepass',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert UserProfile.query.filter_by(username='newuser').first() is not None


def test_register_short_password(client):
    resp = client.post('/register', data={
        'username': 'shortpw',
        'password': 'abc',
    }, follow_redirects=True)
    assert b'at least 6 characters' in resp.data


def test_register_duplicate_username(client):
    client.post('/register', data={'username': 'dupuser', 'password': 'password123'})
    client.get('/logout')
    resp = client.post('/register', data={
        'username': 'dupuser',
        'password': 'password456',
    }, follow_redirects=True)
    assert b'already exists' in resp.data


def test_login_success(client):
    client.post('/register', data={'username': 'loginuser', 'password': 'password123'})
    client.get('/logout')
    resp = client.post('/login', data={
        'username': 'loginuser',
        'password': 'password123',
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_login_wrong_password(client):
    client.post('/register', data={'username': 'wrongpw', 'password': 'password123'})
    client.get('/logout')
    resp = client.post('/login', data={
        'username': 'wrongpw',
        'password': 'wrongpass',
    }, follow_redirects=True)
    assert b'Invalid username or password' in resp.data


def test_logout(auth_client):
    resp = auth_client.get('/logout', follow_redirects=True)
    assert resp.status_code == 200


def test_protected_route_redirects_to_login(client):
    resp = client.get('/')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']
