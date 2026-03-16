from app import app, db, UserProfile

with app.app_context():
    db.create_all()
    print('Tables created')
    profiles = UserProfile.query.all()
    print('Existing profiles:', profiles)
