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
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
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

    with open(file_path, 'r') as f:
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
            return jsonify({
                'success': False,
                'message': 'Only valid @gmail.com addresses are allowed!'
            }), 400

        if User.query.filter_by(username=username).first():
            return jsonify({
                'success': False,
                'message': f'Username "{username}" is already taken. Please choose another one.'
            }), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'This email is already registered.'}), 400

        if len(password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'}), 400

        if not re.match(r'^(?=.*[A-Z])(?=.*\d)(?=.*[a-z])', password):
            return jsonify({
                'success': False,
                'message': 'Password must contain at least one uppercase letter, one lowercase letter, and one digit.'
            }), 400

        if is_password_too_simple(password):
            return jsonify({
                'success': False,
                'message': 'This password is too simple (common). Please try a more complex one.'
            }), 400

        if password != confirm:
            return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return jsonify({'success': True})

    return render_template('register.html')


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
                rating=0
            )
            db.session.add(new_book)
            db.session.commit()
            return jsonify({'id': new_book.id, 'message': 'Book added!'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    books = Book.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': b.id, 'title': b.title, 'author': b.author, 'status': b.status,
        'image_url': b.image_url, 'description': b.description,
        'current_page': b.current_page, 'rating': b.rating
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
            'current_page': book.current_page, 'rating': book.rating
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
    book.rating = data.get('rating', book.rating)

    db.session.commit()
    return jsonify({'success': True})


if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True, ssl_context='adhoc', port=5001)
