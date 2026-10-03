import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "plan.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

# (name, daily target in hours) — inserted once, when the lessons table is empty.
SEED_LESSONS = []


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    if conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO lessons (name, daily_target_hours) VALUES (?, ?)", SEED_LESSONS
        )
    conn.commit()
    conn.close()
