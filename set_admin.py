from app import app, db, User

with app.app_context():
    user = User.query.filter_by(email='maxgrabovi000@gmail.com').first()
    if user:
        user.is_admin = True
        db.session.commit()
        print(f"User {user.username} is now admin")
    else:
        print("User not found.")