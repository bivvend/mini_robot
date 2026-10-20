
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Literal


MemoryType = Literal[
    "fact",
    "experience",
    "interest",
    "desire",
    "preference",
]

MemorySubject = Literal["user", "robot", "world"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SemanticMemory:

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
        return connection

    def _create_tables(self):
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    user_id INTEGER,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 0.5,
                    source TEXT NOT NULL DEFAULT 'manual',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    CHECK (
                        (subject = 'user' AND user_id IS NOT NULL)
                        OR
                        (subject IN ('robot', 'world') AND user_id IS NULL)
                    )
                )
            """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_importance
                ON semantic_memories(importance DESC)
            """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_user
                ON semantic_memories(user_id, importance DESC)
            """)

    
    def add(
        self,
        type: MemoryType,
        subject: MemorySubject,
        content: str,
        importance: float = 0.5,
        source: str = "manual",
        user_id: int | None = None,
    ) -> int:

        if not 0 <= importance <= 1:
            raise ValueError("Importance must be between 0 and 1")

        if subject == "user" and user_id is None:
            raise ValueError("User memories require a user_id")

        if subject != "user" and user_id is not None:
            raise ValueError("Robot/world memories must be global")

        now = utc_now()

        with self._connect() as db:
            existing = db.execute(
                """
                SELECT id
                FROM semantic_memories
                WHERE subject = ?
                AND user_id IS ?
                AND LOWER(TRIM(content)) = LOWER(TRIM(?))
                LIMIT 1
                """,
                (subject, user_id, content),
            ).fetchone()

            if existing:
                return existing["id"]

            
            return db.execute(
                """
                INSERT INTO semantic_memories (
                    type,
                    subject,
                    content,
                    importance,
                    source,
                    created_at,
                    updated_at,
                    user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    type,
                    subject,
                    content,
                    importance,
                    source,
                    now,
                    now,
                    user_id,
                ),
            ).lastrowid


    def get(
        self,
        user_id: int | None = None,
        subject: MemorySubject | None = None,
        type: MemoryType | None = None,
        limit: int = 20,
    ) -> list[dict]:

        query = """
            SELECT *
            FROM semantic_memories
            WHERE (
                (subject = 'user' AND user_id = ?)
                OR
                (subject IN ('robot', 'world') AND user_id IS NULL)
            )
        """

        params = [user_id]

        if subject is not None:
            query += " AND subject = ?"
            params.append(subject)

        if type is not None:
            query += " AND type = ?"
            params.append(type)

        query += """
            ORDER BY importance DESC, updated_at DESC
            LIMIT ?
        """

        params.append(limit)

        with self._connect() as db:
            rows = db.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def update(
        self,
        memory_id: int,
        content: str | None = None,
        importance: float | None = None,
    ):
        if importance is not None and not 0 <= importance <= 1:
            raise ValueError("Importance must be between 0 and 1.")

        changes = []
        params = []

        if content is not None:
            changes.append("content = ?")
            params.append(content)

        if importance is not None:
            changes.append("importance = ?")
            params.append(importance)

        if not changes:
            return

        changes.append("updated_at = ?")
        params.append(utc_now())
        params.append(memory_id)

        with self._connect() as db:
            db.execute(
                f"""
                UPDATE semantic_memories
                SET {', '.join(changes)}
                WHERE id = ?
                """,
                params,
            )

    def delete(self, memory_id: int):
        with self._connect() as db:
            db.execute(
                "DELETE FROM semantic_memories WHERE id = ?",
                (memory_id,),
            )
