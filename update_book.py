# update_book.py
from app import app, db, GlobalMediaCatalog, Book

NEW_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSmK0-vZNHiEqdeDIbObr2jxg8EQLp_qoJy1QYWri0H4A&s=10"
BOOK_TITLE = "A Tale of Two Cities"

with app.app_context():
    # Оновлюємо в глобальному каталозі
    global_item = GlobalMediaCatalog.query.filter_by(title=BOOK_TITLE).first()
    if global_item:
        global_item.image_url = NEW_URL

    # Оновлюємо в книгах користувачів
    user_books = Book.query.filter_by(title=BOOK_TITLE).all()
    for book in user_books:
        book.image_url = NEW_URL

    db.session.commit()
    print("Посилання успішно оновлено в базі даних!")