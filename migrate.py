"""
Run once to migrate existing database.db:
    python migrate.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')
# If your db is in the project root (not instance/), use:
# DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

migrations = [
    "ALTER TABLE book ADD COLUMN media_type VARCHAR(20) DEFAULT 'book'",
    "ALTER TABLE book ADD COLUMN current_season INTEGER DEFAULT 1",
]

for sql in migrations:
    try:
        cur.execute(sql)
        print(f"OK: {sql}")
    except sqlite3.OperationalError as e:
        print(f"SKIP (already exists?): {e}")

conn.commit()
conn.close()
print("Migration done.")