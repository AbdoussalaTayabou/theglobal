"""Migration v3 -> v4 : ajoute colonnes/tables manquantes sans perdre les données.
Idempotent — peut être relancé sans risque.

Usage : python migrate.py
"""
import sqlite3, os
from app import app
from models import db

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chronicle.db")


def col_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())


def table_exists(cur, table):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def add_col(cur, table, col, decl):
    if not col_exists(cur, table, col):
        print(f"  + {table}.{col}")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    else:
        print(f"  = {table}.{col} (déjà présent)")


def main():
    if not os.path.exists(DB_PATH):
        print("Pas de base existante. Lance simplement `python app.py`.")
        return

    print(f"Migration de {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if table_exists(cur, "users"):
        print("[users]")
        add_col(cur, "users", "email", "VARCHAR(255)")
        add_col(cur, "users", "is_active_flag", "BOOLEAN DEFAULT 1")

    if table_exists(cur, "categories"):
        print("[categories]")
        add_col(cur, "categories", "description", "VARCHAR(255) DEFAULT ''")

    if table_exists(cur, "articles"):
        print("[articles]")
        add_col(cur, "articles", "image_caption", "VARCHAR(255) DEFAULT ''")
        add_col(cur, "articles", "image_credit", "VARCHAR(160) DEFAULT ''")
        add_col(cur, "articles", "author_id", "INTEGER")
        add_col(cur, "articles", "meta_description", "VARCHAR(255) DEFAULT ''")
        add_col(cur, "articles", "og_image", "VARCHAR(500) DEFAULT ''")
        add_col(cur, "articles", "status", "VARCHAR(20) DEFAULT 'draft'")
        add_col(cur, "articles", "published_at", "DATETIME")
        add_col(cur, "articles", "views", "INTEGER DEFAULT 0")

        print("  -> sync status depuis l'ancien champ 'published'")
        cur.execute("""UPDATE articles
                       SET status='published',
                           published_at = COALESCE(published_at, created_at)
                       WHERE published = 1 AND (status IS NULL OR status='draft' OR status='')""")
        cur.execute("""UPDATE articles SET status='draft'
                       WHERE published = 0 AND (status IS NULL OR status='')""")

    conn.commit()
    conn.close()

    print("[nouvelles tables] db.create_all()")
    with app.app_context():
        db.create_all()
    print("Migration terminée. Lance maintenant : python app.py")


if __name__ == "__main__":
    main()
