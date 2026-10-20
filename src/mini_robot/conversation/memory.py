
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ConversationMemory:
    def __init__(self, db_path: str | Path | None = None):
        project_root = Path(__file__).resolve().parents[3]

        if db_path is None:
            self.db_path = project_root / "data" / "memory.db"
        else:
            self.db_path = Path(db_path)
            if not self.db_path.is_absolute():
                self.db_path = project_root / self.db_path

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
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    created_at TEXT NOT NULL,
                    last_seen TEXT
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
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
                    FOREIGN KEY(conversation_id)
                        REFERENCES conversations(id)
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS reflection_checkpoints (
                    conversation_id INTEGER PRIMARY KEY,
                    last_message_id INTEGER NOT NULL DEFAULT 0,
                    reflected_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id)
                        REFERENCES conversations(id)
                )
            """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, id)
            """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user
                ON conversations(user_id)
            """)

    def start_conversation(self, user_id: int | None = None) -> int:
        with self._connect() as db:
            return db.execute(
                """
                INSERT INTO conversations (started_at, user_id)
                VALUES (?, ?)
                """,
                (utc_now(), user_id),
            ).lastrowid

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

    def get_conversation_user(self, conversation_id: int) -> int | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT user_id
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()

        if row is None:
            raise ValueError(f"Unknown conversation: {conversation_id}")

        return row["user_id"]

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

    def get_reflection_checkpoint(self, conversation_id: int) -> int:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT last_message_id
                FROM reflection_checkpoints
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()

        return row["last_message_id"] if row else 0


    def set_reflection_checkpoint(
        self,
        conversation_id: int,
        last_message_id: int,
    ):
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO reflection_checkpoints (
                    conversation_id,
                    last_message_id,
                    reflected_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(conversation_id)
                DO UPDATE SET
                    last_message_id = excluded.last_message_id,
                    reflected_at = excluded.reflected_at
                WHERE excluded.last_message_id >
                    reflection_checkpoints.last_message_id
                """,
                (
                    conversation_id,
                    last_message_id,
                    utc_now(),
                ),
            )


    def get_unreviewed_messages(
        self,
        conversation_id: int,
        limit: int = 20,
    ) -> list[dict]:

        checkpoint = self.get_reflection_checkpoint(conversation_id)

        with self._connect() as db:
            rows = db.execute(
                """
                SELECT *
                FROM messages
                WHERE conversation_id = ?
                AND id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (conversation_id, checkpoint, limit),
            ).fetchall()

        return [dict(row) for row in rows]
    