
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class UserProfileStore:
    """Persistent, user-specific profiles for Mini's long-term memory."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def _init_db(self):
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    profile_text TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

    def get(self, user_id: int) -> str | None:
        """Return a user's profile, or None if it doesn't exist."""

        with self._connect() as db:
            row = db.execute("""
                SELECT profile_text
                FROM user_profiles
                WHERE user_id = ?
            """, (user_id,)).fetchone()

        return row["profile_text"] if row else None

    def save(self, user_id: int, profile_text: str):
        """Insert or replace a user's curated profile."""

        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as db:
            db.execute("""
                INSERT INTO user_profiles (
                    user_id,
                    profile_text,
                    updated_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    profile_text = excluded.profile_text,
                    updated_at = excluded.updated_at
            """, (user_id, profile_text, now))

    def get_updated_at(self, user_id: int) -> datetime | None:
        """Return the time a user's profile was last updated."""

        with self._connect() as db:
            row = db.execute("""
                SELECT updated_at
                FROM user_profiles
                WHERE user_id = ?
            """, (user_id,)).fetchone()

        if row is None:
            return None

        return datetime.fromisoformat(row["updated_at"])

    def delete(self, user_id: int):
        """Delete a user's curated profile without deleting their memories."""

        with self._connect() as db:
            db.execute("""
                DELETE FROM user_profiles
                WHERE user_id = ?
            """, (user_id,))

    def build_prompt(self, user_id: int) -> str:
        """Return a ready-to-use prompt section for this user."""

        profile = self.get(user_id)

        if not profile or not profile.strip():
            return ""

        return (
            "LONG-TERM MEMORY ABOUT THE CURRENT USER:\n"
            f"{profile.strip()}\n\n"
            "This information comes from previous conversations. "
            "Use it naturally when relevant, without repeatedly "
            "mentioning remembered details. "
            "Treat it as potentially outdated and accept corrections "
            "from the current user. "
            "Do not confuse this user's information with anyone else's."
        )
