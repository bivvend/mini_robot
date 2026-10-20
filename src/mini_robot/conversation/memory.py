
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ConversationMemory:

    def __init__(self, db_path="data/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._create_tables()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _create_tables(self):
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    emotion TEXT,
                    gesture TEXT,
                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id)
                )
            """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, id)
            """)

    def start_conversation(self) -> int:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO conversations (started_at) VALUES (?)",
                (utc_now(),),
            )
            return cursor.lastrowid

    def end_conversation(self, conversation_id: int):
        with self._connect() as db:
            db.execute(
                """
                UPDATE conversations
                SET ended_at = ?
                WHERE id = ?
                """,
                (utc_now(), conversation_id),
            )

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        emotion: str | None = None,
        gesture: str | None = None,
    ) -> int:

        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO messages (
                    conversation_id,
                    timestamp,
                    role,
                    content,
                    emotion,
                    gesture
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    utc_now(),
                    role,
                    content,
                    emotion,
                    gesture,
                ),
            )

            return cursor.lastrowid

    def get_messages(
        self,
        conversation_id: int,
        limit: int | None = None,
    ) -> list[dict]:

        query = """
            SELECT *
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
        """

        parameters = [conversation_id]

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)

        with self._connect() as db:
            rows = db.execute(query, parameters).fetchall()

        return [dict(row) for row in reversed(rows)]
