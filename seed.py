# seed.py
from app import app, db, GlobalMediaCatalog
from catalog_data import INITIAL_MEDIA_DATA

def seed_database():
    with app.app_context():
        added_count = 0
        for item in INITIAL_MEDIA_DATA:
            # Перевіряємо, чи є вже такий тайтл у конкретній категорії
            exists = GlobalMediaCatalog.query.filter_by(
                title=item["title"],
                category=item["category"]
            ).first()

            if not exists:
                new_item = GlobalMediaCatalog(
                    title=item["title"],
                    creator=item["creator"],
                    category=item["category"],
                    image_url=item["image_url"]
                )
                db.session.add(new_item)
                added_count += 1
                print(f"➕ Додано: {item['title']} ({item['category']})")

        db.session.commit()
        print(f"\n Успішно! Додано нових об'єктів: {added_count}")

if __name__ == "__main__":
    seed_database()