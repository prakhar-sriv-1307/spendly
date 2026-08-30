"""Database layer for Spendly.

Implements the SQLite data foundation the rest of the app builds on:

    get_db()   — open a connection (Row factory + foreign keys enabled)
    init_db()  — create tables with CREATE TABLE IF NOT EXISTS (idempotent)
    seed_db()  — insert demo data once (a demo user + 8 sample expenses)

No ORM, standard-library sqlite3 only, parameterized queries throughout.
Run directly to build and seed a fresh database:  python -m database.db
"""

import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

# Database file lives at the project root (ignored by git; see .gitignore).
DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

# Fixed category list shared across the app.
CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses (user_id);
"""


def get_db():
    """Open and return a SQLite connection to the project database.

    Rows are returned as ``sqlite3.Row`` (dict-like access) and foreign key
    enforcement is enabled for the connection. The caller owns the connection
    and is responsible for closing it.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create both tables if they don't already exist. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert demo data once.

    Returns early if the users table already has rows, so repeated calls never
    duplicate records.
    """
    conn = get_db()
    try:
        (user_count,) = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        if user_count > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (
                "Demo User",
                "demo@spendly.com",
                # pbkdf2 rather than the werkzeug default (scrypt), which this
                # Python build's hashlib lacks. Portable and check-compatible.
                generate_password_hash("demo123", method="pbkdf2:sha256"),
            ),
        )
        user_id = cursor.lastrowid

        # 8 expenses across all seven categories (Food appears twice),
        # dates spread across the current month, amounts stored as REAL.
        sample_expenses = [
            (user_id, 32.50, "Food", "2026-08-03", "Groceries"),
            (user_id, 8.75, "Food", "2026-08-14", "Coffee run"),
            (user_id, 45.00, "Transport", "2026-08-05", "Metro pass"),
            (user_id, 120.00, "Bills", "2026-08-07", "Electricity"),
            (user_id, 60.00, "Health", "2026-08-10", "Pharmacy"),
            (user_id, 18.99, "Entertainment", "2026-08-12", "Movie ticket"),
            (user_id, 89.90, "Shopping", "2026-08-16", "New shoes"),
            (user_id, 15.00, "Other", "2026-08-18", "Misc"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            sample_expenses,
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    seed_db()
    print(f"Database ready at {DB_PATH}")
