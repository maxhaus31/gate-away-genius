import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "feedback.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                rating      INTEGER,
                email       TEXT,
                message     TEXT,
                submitted_at TEXT NOT NULL
            )
        """)
        conn.commit()


def insert_feedback(rating: int | None, email: str | None, message: str | None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO feedback (rating, email, message, submitted_at) VALUES (?, ?, ?, ?)",
            (rating, email or None, message or None, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
