
import logging
from datetime import datetime, timezone
import sqlite3

from pydantic import BaseModel, Field

from mini_robot.conversation.user_profile import UserProfileStore

logger = logging.getLogger(__name__)


class CuratedUserProfile(BaseModel):
    """Structured response from the profile-curation LLM."""

    profile_text: str = Field(
        description=(
            "A concise, factual summary of the user's known "
            "interests, preferences, background and ongoing projects."
        )
    )


class UserProfileCurator:
    """Consolidates stored user memories into a persistent profile."""

    def __init__(
        self,
        llm,
        conversation_memory,
        profile_store: UserProfileStore,
        max_memories: int | None = None,
    ):
        self.llm = llm
        self.memory = conversation_memory
        self.profile_store = profile_store
        self.max_memories = max_memories

    
    def needs_update(self, user_id: int) -> bool:
        """Check whether a user's memories have changed since curation."""

        profile_updated = self.profile_store.get_updated_at(user_id)

        if profile_updated is None:
            return True

        with sqlite3.connect(self.memory.db_path) as db:
            row = db.execute(
                """
                SELECT MAX(updated_at)
                FROM semantic_memories
                WHERE subject = 'user'
                AND user_id = ?
                """,
                (user_id,),
            ).fetchone()

        if row[0] is None:
            return False

        memory_updated = datetime.fromisoformat(row[0])

        return memory_updated > profile_updated



    def _get_user_memories(self, user_id: int) -> list[dict]:
        """
        Retrieve all semantic memories belonging to one user.

        Includes memories from previous conversations, but excludes
        robot and world memories and all other users.
        """
        with sqlite3.connect(self.memory.db_path) as db:
            db.row_factory = sqlite3.Row

            rows = db.execute(
                """
                SELECT
                    id,
                    type,
                    content,
                    importance,
                    created_at,
                    updated_at
                FROM semantic_memories
                WHERE subject = 'user'
                AND user_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (user_id,),
            ).fetchall()

        memories = [dict(row) for row in rows]

        if self.max_memories is not None:
            memories = memories[-self.max_memories:]

        return memories


    def curate(self, user_id: int) -> str | None:
        """
        Generate and save a consolidated profile for one user.

        Returns the updated profile text, or None if there are
        no stored memories.
        """
        memories = self._get_user_memories(user_id)

        if not memories:
            logger.debug(
                "No memories available for user %s",
                user_id,
            )
            return None

        previous_profile = self.profile_store.get(user_id)

        memory_text = "\n".join(
            (
                f"- [{memory['type']}] "
                f"{memory['content']} "
                f"(importance={memory['importance']:.2f}, "
                f"recorded={memory['created_at']}, "
                f"updated={memory['updated_at']})"
            )
            for memory in memories
        )

        system_prompt = """
You are maintaining the long-term memory of a conversational robot.

Your task is to produce a concise and accurate profile of a user
based on memories extracted from previous conversations.

Include:
- Stable personal facts and background.
- Interests, hobbies and preferences.
- Important ongoing projects.
- Relevant relationships and recurring topics.
- Changes in interests or preferences over time.

Rules:
- Only include information supported by the supplied memories.
- Never invent facts or infer personal details without evidence.
- Merge duplicate and overlapping memories.
- Prefer newer information when facts contradict.
- Preserve useful details rather than making the profile generic.
- Avoid temporary or unimportant conversational details.
- Write in the third person.
- Aim for approximately 300–600 words.
- Do not include instructions addressed to the robot.
- Return only the requested structured response.
""".strip()

        user_prompt = f"""
USER ID: {user_id}

PREVIOUS CURATED PROFILE:
{previous_profile or "(none)"}

STORED MEMORIES:
{memory_text}

Generate an updated user profile using the stored memories.
""".strip()

        logger.info(
            "Curating user profile %s from %d memories",
            user_id,
            len(memories),
        )

        result = self.llm.generate_structured(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_model=CuratedUserProfile,
        )

        profile = result.profile_text.strip()

        if not profile:
            logger.warning(
                "Curator returned an empty profile for user %s",
                user_id,
            )
            return None

        self.profile_store.save(user_id, profile)

        logger.info(
            "Updated profile for user %s (%d characters)",
            user_id,
            len(profile),
        )

        return profile
