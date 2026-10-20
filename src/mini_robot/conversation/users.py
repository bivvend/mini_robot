import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class UserManager:

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._create_table()

    def _connect(self):
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def _create_table(self):
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    created_at TEXT NOT NULL,
                    last_seen TEXT
                )
            """)

    def get_or_create(self, name: str) -> dict:
        name = name.strip()

        if not name:
            raise ValueError("User name cannot be empty")

        now = utc_now()

        with self._connect() as db:
            db.execute(
                """
                INSERT INTO users (name, created_at, last_seen)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    last_seen = excluded.last_seen
                """,
                (name, now, now),
            )

            row = db.execute(
                "SELECT * FROM users WHERE name = ? COLLATE NOCASE",
                (name,),
            ).fetchone()

        return dict(row)

    def get(self, name: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM users WHERE name = ? COLLATE NOCASE",
                (name.strip(),),
            ).fetchone()

        return dict(row) if row else None
