"""Copie les données d'une base SQLite existante vers PostgreSQL.

Usage :
    1. Configure DATABASE_URL (PostgreSQL cible) dans .env
    2. Assure-toi que la base PG est créée et que `flask db upgrade` a été
       exécuté (ou qu'`init_db()` a créé le schéma).
    3. python migrate_sqlite_to_pg.py [chemin/vers/chronicle.db]

Le script copie table par table dans l'ordre des dépendances FK, puis
remet à jour les séquences PostgreSQL.
"""
import os
import sys
import sqlite3
from sqlalchemy import create_engine, MetaData, text

SQLITE_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "chronicle.db"
)

PG_URL = os.environ.get("DATABASE_URL", "").strip()
if PG_URL.startswith("postgres://"):
    PG_URL = PG_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif PG_URL.startswith("postgresql://") and "+psycopg2" not in PG_URL:
    PG_URL = PG_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if not PG_URL or not PG_URL.startswith("postgresql"):
    sys.exit("DATABASE_URL doit pointer vers PostgreSQL (postgresql+psycopg2://...).")

if not os.path.exists(SQLITE_PATH):
    sys.exit(f"Fichier SQLite introuvable : {SQLITE_PATH}")

print(f"Source SQLite : {SQLITE_PATH}")
print(f"Cible Postgres : {PG_URL.split('@')[-1]}")

sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

pg_engine = create_engine(PG_URL)
md = MetaData()
md.reflect(bind=pg_engine)

# Ordre topologique (parents avant enfants) via SQLAlchemy
ordered_tables = md.sorted_tables

with pg_engine.begin() as pg:
    # Désactive les contraintes le temps de l'import
    pg.execute(text("SET session_replication_role = 'replica'"))

    for table in ordered_tables:
        name = table.name
        if name == "alembic_version":
            continue
        # Vérifier que la table existe côté SQLite
        cur = sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
        )
        if not cur.fetchone():
            print(f"  - {name} : absent côté SQLite, skip")
            continue

        rows = sqlite_conn.execute(f"SELECT * FROM {name}").fetchall()
        if not rows:
            print(f"  = {name} : vide")
            continue

        cols = rows[0].keys()
        # Filtrer aux colonnes présentes côté PG
        pg_cols = {c.name for c in table.columns}
        keep = [c for c in cols if c in pg_cols]

        data = [{c: r[c] for c in keep} for r in rows]
        # Vide la table cible pour éviter les doublons (CASCADE car FK)
        pg.execute(text(f'TRUNCATE TABLE "{name}" RESTART IDENTITY CASCADE'))
        pg.execute(table.insert(), data)
        print(f"  + {name} : {len(data)} lignes")

    pg.execute(text("SET session_replication_role = 'origin'"))

    # Remet à jour les séquences sur les colonnes id auto-increment
    for table in ordered_tables:
        for col in table.columns:
            if col.primary_key and col.autoincrement and str(col.type).lower().startswith("int"):
                seq = f'{table.name}_{col.name}_seq'
                try:
                    pg.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('\"{table.name}\"', '{col.name}'), "
                        f"COALESCE((SELECT MAX({col.name}) FROM \"{table.name}\"), 1))"
                    ))
                except Exception as e:
                    print(f"  ! séquence {seq} : {e}")

print("Migration terminée.")
