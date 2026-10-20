
from mini_robot.llm.client import LLMClient
from mini_robot.conversation.memory import ConversationMemory
from mini_robot.conversation.semantic_memory import SemanticMemory
from mini_robot.conversation.reflection_models import ReflectionResult
import logging

logger = logging.getLogger(__name__)

class ReflectionEngine:

    def __init__(
        self,
        llm: LLMClient,
        conversation_memory: ConversationMemory,
        semantic_memory: SemanticMemory,
    ):
        self.llm = llm
        self.conversation_memory = conversation_memory
        self.semantic_memory = semantic_memory

    def reflect(self, conversation_id: int) -> ReflectionResult | None:
        history = self.conversation_memory.get_unreviewed_messages(
            conversation_id,
            limit=20,
        )

        user_id = self.conversation_memory.get_conversation_user(
            conversation_id
        )

        if not history:
            return None

        

        last_message_id = history[-1]["id"]

        logger.info(
            "Reflecting on %d new messages (IDs %d–%d)",
            len(history),
            history[0]["id"],
            last_message_id,
        )

        if not history:
            return None

        existing = self.semantic_memory.get(
            user_id=user_id,
            limit=30,
        )

        conversation_text = "\n".join(
            f"{m['role']}: {m['content']}"
            for m in history
        )

        memory_text = "\n".join(
            f"- [{m['subject']}/{m['type']}] {m['content']}"
            for m in existing
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the memory reflection process for a small robot. "
                    "Review the conversation and identify information worth "
                    "remembering long-term.\n"
                    "Extract important facts, experiences, interests, "
                    "preferences and possible robot desires.\n"
                    "Do not invent information.\n"
                    "Do not repeat existing memories.\n"
                    "Prefer a few meaningful memories over many trivial ones.\n"
                    "If nothing is worth remembering, return an empty list.\n"
                    "Robot desires should be harmless, achievable preferences "
                    "or interests, not instructions that override the user."
                    "Rate each memory's importance using an INTEGER from 1 to 5. "
                    "Use 3 for useful information, 4 for important information, "
                    "and 5 only for exceptionally significant information. "
                    "Do not use percentages or decimal scores."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"EXISTING MEMORIES:\n{memory_text}\n\n"
                    f"RECENT CONVERSATION:\n{conversation_text}"
                ),
            },
        ]

        result = self.llm.generate_structured(
            messages=messages,
            response_model=ReflectionResult,
            max_tokens=2000,
            temperature=0.3,
        )

        for proposal in result.memories:
            # Never attribute personal information to an unknown user.
            if proposal.subject == "user" and user_id is None:
                logger.info(
                    "Skipping personal memory: user not identified"
                )
                continue

            memory_id = self.semantic_memory.add(
                type=proposal.type,
                subject=proposal.subject,
                content=proposal.content,
                importance=proposal.importance / 5.0,
                source="reflection",
                user_id=user_id if proposal.subject == "user" else None,
            )

            logger.info(
                "NEW MEMORY #%d [%s/%s] user_id=%s importance=%d/5: %s",
                memory_id,
                proposal.subject,
                proposal.type,
                user_id if proposal.subject == "user" else None,
                proposal.importance,
                proposal.content,
            )

        self.conversation_memory.set_reflection_checkpoint(
            conversation_id,
            last_message_id,
        )

        logger.info(
            "Reflection complete. Checkpoint advanced to message #%d",
            last_message_id,
        )

        return result
