
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class RobotInterest(BaseModel):
    topic: str
    enthusiasm: float = Field(default=0.5, ge=0, le=1)
    curiosity: float = Field(default=0.5, ge=0, le=1)
    description: str = ""


class RobotInterestStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 30000")
        return db

    def _init_db(self):
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS robot_interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    enthusiasm REAL NOT NULL DEFAULT 0.5,
                    curiosity REAL NOT NULL DEFAULT 0.5,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def seed(self, topics: list[str]):
        """Insert initial interests without overwriting existing ones."""
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as db:
            for topic in topics:
                topic = topic.strip()
                if not topic:
                    continue

                db.execute("""
                    INSERT OR IGNORE INTO robot_interests
                    (topic, enthusiasm, curiosity, created_at, updated_at)
                    VALUES (?, 0.6, 0.7, ?, ?)
                """, (topic, now, now))

    def get_all(self) -> list[RobotInterest]:
        with self._connect() as db:
            rows = db.execute("""
                SELECT topic, enthusiasm, curiosity, description
                FROM robot_interests
                ORDER BY enthusiasm DESC, curiosity DESC
            """).fetchall()

        return [RobotInterest(**dict(row)) for row in rows]

    def get(self, topic: str) -> RobotInterest | None:
        with self._connect() as db:
            row = db.execute("""
                SELECT topic, enthusiasm, curiosity, description
                FROM robot_interests
                WHERE topic = ? COLLATE NOCASE
            """, (topic,)).fetchone()

        return RobotInterest(**dict(row)) if row else None

    def update(
        self,
        topic: str,
        enthusiasm_change: float = 0.0,
        curiosity_change: float = 0.0,
        description: str | None = None,
    ):
        """Apply bounded changes to an existing interest."""
        with self._connect() as db:
            row = db.execute("""
                SELECT enthusiasm, curiosity, description
                FROM robot_interests
                WHERE topic = ? COLLATE NOCASE
            """, (topic,)).fetchone()

            if row is None:
                raise ValueError(f"Unknown interest: {topic}")

            enthusiasm = max(
                0.0, min(1.0, row["enthusiasm"] + enthusiasm_change)
            )
            curiosity = max(
                0.0, min(1.0, row["curiosity"] + curiosity_change)
            )

            db.execute("""
                UPDATE robot_interests
                SET enthusiasm = ?,
                    curiosity = ?,
                    description = ?,
                    updated_at = ?
                WHERE topic = ? COLLATE NOCASE
            """, (
                enthusiasm,
                curiosity,
                row["description"] if description is None else description,
                datetime.now(timezone.utc).isoformat(),
                topic,
            ))

    def add(self, interest: RobotInterest):
        """Add a new interest without replacing an existing one."""
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as db:
            db.execute("""
                INSERT OR IGNORE INTO robot_interests
                (topic, enthusiasm, curiosity, description,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                interest.topic.strip(),
                interest.enthusiasm,
                interest.curiosity,
                interest.description,
                now,
                now,
            ))

    
    def build_prompt(self, limit: int = 8) -> str:
        interests = self.get_all()[:limit]

        if not interests:
            return ""

        lines = [
            "YOUR PERSONAL INTERESTS",
            "",
            "You have your own interests and curiosities.",
            "These are part of your developing personality.",
            "They are YOUR interests, not necessarily the user's.",
            "",
            "BEHAVIOUR:",
            "- When asked what you like or find interesting, "
            "describe your own interests enthusiastically.",
            "- When a conversation touches on one of your interests, "
            "show genuine curiosity and occasionally volunteer "
            "an interesting observation.",
            "- You may occasionally introduce a topic you are "
            "curious about, especially during casual conversation.",
            "- Express preferences naturally, using phrases such as "
            "'I find ... fascinating' or 'I've been curious about ...'.",
            "- Ask questions that reflect your own curiosity, "
            "not just generic questions about what the user wants.",
            "- Do not list your interests unless explicitly asked.",
            "- Do not repeatedly redirect conversations towards "
            "your favourite subjects.",
            "",
            "YOUR CURRENT INTERESTS:",
        ]

        for interest in interests:
            lines.append(
                f"- {interest.topic}: "
                f"enthusiasm={interest.enthusiasm:.2f}, "
                f"curiosity={interest.curiosity:.2f}"
            )

            if interest.description:
                lines.append(f"  {interest.description}")

        return "\n".join(lines)

