"""SQLite storage layer for budgeteer.

Amounts are stored as integer minor units (cents) to avoid float
rounding errors. Dates are stored as ISO strings (YYYY-MM-DD).
"""

import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    kind     TEXT NOT NULL CHECK (kind IN ('expense', 'income')),
    amount   INTEGER NOT NULL CHECK (amount > 0),
    category TEXT NOT NULL,
    date     TEXT NOT NULL,
    note     TEXT NOT NULL DEFAULT '',
    account  TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('expense', 'income', 'both'))
);

CREATE TABLE IF NOT EXISTS budgets (
    category TEXT NOT NULL,
    month    TEXT NOT NULL,
    limit_amount INTEGER NOT NULL CHECK (limit_amount > 0),
    PRIMARY KEY (category, month)
);

CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);
"""

DEFAULT_CATEGORIES = [
    ("food", "expense"),
    ("transport", "expense"),
    ("housing", "expense"),
    ("utilities", "expense"),
    ("entertainment", "expense"),
    ("health", "expense"),
    ("shopping", "expense"),
    ("other", "expense"),
    ("salary", "income"),
    ("freelance", "income"),
    ("interest", "income"),
    ("gift", "income"),
]


def default_db_path() -> Path:
    env = os.environ.get("BUDGETEER_DB")
    if env:
        return Path(env).expanduser()
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home).expanduser() if data_home else Path.home() / ".local" / "share"
    return base / "budgeteer" / "budgeteer.db"


def connect(db_path=None) -> sqlite3.Connection:
    path = Path(db_path).expanduser() if db_path else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # Seed default categories on first run (INSERT OR IGNORE keeps user edits).
    conn.executemany(
        "INSERT OR IGNORE INTO categories (name, kind) VALUES (?, ?)",
        DEFAULT_CATEGORIES,
    )
    conn.commit()
    return conn
