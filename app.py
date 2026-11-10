from urllib.parse import urlparse
from datetime import datetime
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
import os
import random
import re
import pytz
import requests
from flask import (
    Flask,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from catalog_data import INITIAL_MEDIA_DATA

app = Flask(__name__)

# Налаштування безпеки та конфігурації
Talisman(app, content_security_policy=None, force_https=True)

app.config["SECRET_KEY"] = "dev-secure-key-2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# =====================================================================
# 🔐 НАЛАШТУВАННЯ GMAIL ТА ЛОГУВАННЯ
# =====================================================================
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = "maxgrabovi000@gmail.com"
app.config["MAIL_PASSWORD"] = "trvu ddtg cggo owmm"  # Або твій актуальний пароль додатку
app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]

mail = Mail(app)

handler = RotatingFileHandler("security.log", maxBytes=10000, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "api_login"

local_tz = pytz.timezone("Europe/Warsaw")


def is_safe_next(url):
    """Дозволяємо лише локальні шляхи (захист від open redirect)."""
    if not url or not url.startswith("/") or url.startswith("//") or "\\" in url:
        return False
    parsed = urlparse(url)
    return not parsed.scheme and not parsed.netloc


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/books"):
        return jsonify({"error": "Authentication required"}), 401
    return redirect(url_for("api_login", next=request.full_path.rstrip("?")))


# =====================================================================
# 📦 БАЗА ДАНИХ (МОДЕЛІ)
# =====================================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    books = db.relationship("Book", backref="owner", lazy=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=db.func.now())


class Book(db.Model):
    __table_args__ = {"extend_existing": True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200))
    status = db.Column(db.String(50), default="In plan")
    image_url = db.Column(db.String(500), default="")
    description = db.Column(db.Text, default="")
    current_page = db.Column(db.Integer, default=0)
    rating = db.Column(db.Integer, default=0)
    media_type = db.Column(db.String(20), default="book")
    current_season = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class GlobalMediaCatalog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    creator = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=db.func.now())


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def seed_media_catalog():
    if GlobalMediaCatalog.query.first() is None:
        for item in INITIAL_MEDIA_DATA:
            db.session.add(GlobalMediaCatalog(**item))
        db.session.commit()
        print("Каталог медіа успішно заповнено початковими даними!")


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({"success": False, "message": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(local_tz)
        db.session.commit()


# =====================================================================
# 🌐 МАРШРУТИ (ROUTES)
# =====================================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/force-seed")
def force_seed():
    db.create_all()
    seed_media_catalog()
    return "Каталог успішно створено та заповнено!"


@app.route("/api/auth/status")
def auth_status():
    if current_user.is_authenticated:
        return jsonify({"logged_in": True, "username": current_user.username})
    return jsonify({"logged_in": False})


@app.route("/api/auth/login", methods=["GET", "POST"])
def api_login():
    next_url = request.args.get("next", "")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(next_url if is_safe_next(next_url) else url_for("index"))
        flash("Invalid username or password")
    return render_template("login.html")


@app.route("/api/auth/register", methods=["GET", "POST"])
def api_register():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form

        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        confirm = data.get("confirm_password", "")

        if not username or not email or not password:
            return jsonify({"success": False, "message": "All fields are required."}), 400

        if password != confirm:
            return jsonify({"success": False, "message": "Passwords do not match."}), 400

        if not email.endswith("@gmail.com"):
            return jsonify({"success": False, "message": "Only valid @gmail.com addresses are allowed!"}), 400

        try:
            if User.query.filter_by(username=username).first():
                return jsonify({"success": False, "message": "This username is already taken. Try another one."}), 400

            if User.query.filter_by(email=email).first():
                return jsonify({"success": False, "message": "An account with this email already exists."}), 400
        except Exception as e:
            app.logger.error(f"DB Check error: {str(e)}")

        verification_code = str(random.randint(100000, 999999))

        session["temp_user_data"] = {
            "username": username,
            "email": email,
            "password": generate_password_hash(password, method="pbkdf2:sha256"),
        }
        session["verification_code"] = verification_code

        try:
            msg = Message(
                subject="Confirm your registration at Secure Library",
                recipients=[email]
            )
            msg.body = (
                f"Hello {username},\n\n"
                f"Thank you for creating an account with Secure Library Application.\n"
                f"To complete your registration, please use this 6-digit verification code:\n\n"
                f"Verification Code: {verification_code}\n\n"
                f"Best regards,\nSecure Library Support Team"
            )
            mail.send(msg)
            return jsonify({"success": True, "action": "requires_verification"})
        except Exception as e:
            app.logger.error(f"Failed to send email to {email}: {str(e)}")
            return jsonify({"success": False, "message": "Failed to send verification email."}), 500

    return render_template("register.html")


@app.route("/api/auth/verify-code", methods=["POST"])
def verify_code():
    data = request.get_json()
    user_code = data.get("code", "").strip()

    saved_code = session.get("verification_code")
    temp_data = session.get("temp_user_data")

    if not saved_code or not temp_data:
        return jsonify({"success": False, "message": "Session expired. Please register again."}), 400

    if user_code == saved_code:
        try:
            new_user = User(
                username=temp_data["username"],
                email=temp_data["email"],
                password=temp_data["password"],
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)

            session.pop("verification_code", None)
            session.pop("temp_user_data", None)

            return jsonify({"success": True, "message": "Correct verification code! Welcome."})
        except Exception as db_err:
            db.session.rollback()
            return jsonify({"success": False, "message": "Database error occurred."}), 500
    else:
        return jsonify({"success": False, "message": "Invalid verification code."}), 400


@app.route("/api/auth/logout")
def api_logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/api/books", methods=["GET", "POST"])
@login_required
def handle_books():
    if request.method == "POST":
        try:
            data = request.get_json()
            if not data or "title" not in data:
                return jsonify({"error": "Title is required"}), 400

            title = data["title"].strip()
            media_type = data.get("media_type", "book")
            author = data.get("author", "").strip()

            global_item = GlobalMediaCatalog.query.filter(
                GlobalMediaCatalog.category == media_type,
                GlobalMediaCatalog.title.ilike(title)
            ).first()

            image_url = ""
            if global_item:
                if global_item.image_url:
                    image_url = global_item.image_url
                if not author and global_item.creator:
                    author = global_item.creator

            new_book = Book(
                title=title,
                author=author,
                user_id=current_user.id,
                description="",
                image_url=image_url,
                current_page=0,
                current_season=1,
                rating=0,
                media_type=media_type,
            )
            db.session.add(new_book)
            db.session.commit()
            return jsonify({"id": new_book.id, "message": "Item added!"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    media_type = request.args.get("type", "book")
    books = Book.query.filter_by(user_id=current_user.id, media_type=media_type).all()
    return jsonify([{
        "id": b.id, "title": b.title, "author": b.author, "status": b.status,
        "image_url": b.image_url, "description": b.description,
        "current_page": b.current_page, "current_season": b.current_season,
        "rating": b.rating, "media_type": b.media_type
    } for b in books])


@app.route("/api/books/<int:id>", methods=["GET", "PUT", "DELETE"])
@login_required
def modify_book(id):
    book = Book.query.get_or_404(id)
    if book.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403

    if request.method == "GET":
        return jsonify({
            "id": book.id, "title": book.title, "author": book.author, "status": book.status,
            "image_url": book.image_url, "description": book.description,
            "current_page": book.current_page, "current_season": book.current_season,
            "rating": book.rating, "media_type": book.media_type
        })

    if request.method == "DELETE":
        db.session.delete(book)
        db.session.commit()
        return jsonify({"success": True})

    data = request.get_json()
    book.status = data.get("status", book.status)
    book.image_url = data.get("image_url", book.image_url)
    book.description = data.get("description", book.description)
    book.current_page = data.get("current_page", book.current_page)
    book.current_season = data.get("current_season", book.current_season)
    book.rating = data.get("rating", book.rating)

    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/search-suggestions", methods=["GET"])
def search_suggestions():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "book")

    if not query or len(query) < 2:
        return jsonify([])

    results = GlobalMediaCatalog.query.filter(
        GlobalMediaCatalog.category == category,
        GlobalMediaCatalog.title.ilike(f"%{query}%"),
    ).limit(7).all()

    suggestions = [{"title": item.title, "author": item.creator or ""} for item in results]
    return jsonify(suggestions)


# Адмін панель
@app.route("/api/admin/users")
@login_required
@admin_required
def api_admin_panel():
    users = User.query.all()
    return render_template("admin.html", users=users)


@app.route("/api/admin/delete_user/<int:user_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({"success": False, "message": "You cannot delete yourself!"}), 400

    Book.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"success": True, "message": f"User {user.username} deleted"})


@app.route("/api/admin/clear_books/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def clear_books(user_id):
    Book.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({"success": True})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_media_catalog()
    app.run(debug=True, ssl_context="adhoc", port=5000)