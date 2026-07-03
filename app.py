import random
from flask import session
import os
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pytz
from datetime import datetime
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import make_response, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

Talisman(app, content_security_policy=None, force_https=True)

app.config['SECRET_KEY'] = 'dev-secure-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

handler = RotatingFileHandler('security.log', maxBytes=10000, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)


db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'api_login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    books = db.relationship('Book', backref='owner', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=db.func.now())


class Book(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200))
    status = db.Column(db.String(50), default='In plan')
    image_url = db.Column(db.String(500), default='')
    description = db.Column(db.Text, default='')
    current_page = db.Column(db.Integer, default=0)
    rating = db.Column(db.Integer, default=0)
    media_type = db.Column(db.String(20), default='book')
    current_season = db.Column(db.Integer, default=1)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)

    return decorated_function


@app.route('/api/admin/users')
@login_required
@admin_required
def api_admin_panel():
    users = User.query.all()
    return render_template('admin.html', users=users)


local_tz = pytz.timezone('Europe/Warsaw')


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(local_tz)
        db.session.commit()


@app.route('/api/admin/delete_user/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'You cannot delete yourself!'}), 400

    Book.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': f'User {user.username} deleted'})


@app.route('/api/admin/clear_books/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def clear_books(user_id):
    Book.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({'success': True})


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/auth/status')
def auth_status():
    if current_user.is_authenticated:
        return jsonify({'logged_in': True, 'username': current_user.username})
    return jsonify({'logged_in': False})


@app.route('/api/auth/login', methods=['GET', 'POST'])
def api_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=db.func.now())


def is_password_too_simple(password):
    file_path = 'common_passwords.txt'
    if not os.path.exists(file_path):
        return False

    with open("common_passwords.txt", encoding="utf-8") as f:
        common_passwords = [line.strip() for line in f.readlines()]

    return password in common_passwords


@app.route('/api/auth/register', methods=['GET', 'POST'])
def api_register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form

        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm = data.get('confirm_password', '')

        gmail_pattern = r'^[a-z0-9._%+-]+@gmail\.com$'
        if not re.match(gmail_pattern, email):
            return jsonify({'success': False, 'message': 'Only valid @gmail.com addresses are allowed!'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': f'Username "{username}" is already taken.'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'This email is already registered.'}), 400

        if len(password) < 8 or not re.match(r'^(?=.*[A-Z])(?=.*\d)(?=.*[a-z])', password):
            return jsonify({'success': False, 'message': 'Password does not meet security requirements.'}), 400

        if is_password_too_simple(password):
            return jsonify({'success': False, 'message': 'This password is too simple.'}), 400

        if password != confirm:
            return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400

        verification_code = str(random.randint(100000, 999999))

        session['temp_user_data'] = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password, method='pbkdf2:sha256')
        }
        session['verification_code'] = verification_code

        print(f"\n[MAIL SIMULATOR] To: {email} | Your verification code is: {verification_code}\n")
        app.logger.info(f"Verification code sent to {email}: {verification_code}")

        return jsonify({'success': True, 'action': 'requires_verification'})

    return render_template('register.html')


@app.route('/api/auth/verify-code', methods=['POST'])
def verify_code():
    data = request.get_json()
    user_code = data.get('code', '').strip()

    saved_code = session.get('verification_code')
    temp_data = session.get('temp_user_data')

    if not saved_code or not temp_data:
        return jsonify({'success': False, 'message': 'Session expired. Please try registering again.'}), 400

    if user_code == saved_code:
        new_user = User(
            username=temp_data['username'],
            email=temp_data['email'],
            password=temp_data['password']
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        session.pop('verification_code', None)
        session.pop('temp_user_data', None)

        return jsonify({'success': True, 'message': 'Correct verification code! Welcome.'})
    else:
        return jsonify({'success': False, 'message': 'Invalid verification code. Please try again.'}), 400

@app.route('/api/auth/logout')
def api_logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/api/books', methods=['GET', 'POST'])
@login_required
def handle_books():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data or 'title' not in data:
                return jsonify({'error': 'Title is required'}), 400

            new_book = Book(
                title=data['title'],
                author=data.get('author', ''),
                user_id=current_user.id,
                description='',
                image_url='',
                current_page=0,
                current_season=1,
                rating=0,
                media_type=data.get('media_type', 'book'),
            )
            db.session.add(new_book)
            db.session.commit()
            return jsonify({'id': new_book.id, 'message': 'Item added!'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    media_type = request.args.get('type', 'book')
    books = Book.query.filter_by(user_id=current_user.id, media_type=media_type).all()
    return jsonify([{
        'id': b.id, 'title': b.title, 'author': b.author, 'status': b.status,
        'image_url': b.image_url, 'description': b.description,
        'current_page': b.current_page, 'current_season': b.current_season,
        'rating': b.rating, 'media_type': b.media_type
    } for b in books])


@app.route('/api/books/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def modify_book(id):
    book = Book.query.get_or_404(id)
    if book.user_id != current_user.id:
        return jsonify({'error': 'Forbidden'}), 403

    if request.method == 'GET':
        return jsonify({
            'id': book.id, 'title': book.title, 'author': book.author, 'status': book.status,
            'image_url': book.image_url, 'description': book.description,
            'current_page': book.current_page, 'current_season': book.current_season,
            'rating': book.rating, 'media_type': book.media_type
        })

    if request.method == 'DELETE':
        db.session.delete(book)
        db.session.commit()
        return jsonify({'success': True})

    data = request.get_json()
    book.status = data.get('status', book.status)
    book.image_url = data.get('image_url', book.image_url)
    book.description = data.get('description', book.description)
    book.current_page = data.get('current_page', book.current_page)
    book.current_season = data.get('current_season', book.current_season)
    book.rating = data.get('rating', book.rating)

    db.session.commit()
    return jsonify({'success': True})


if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True, ssl_context='adhoc', port=5000)