
from mini_robot.llm.client import LLMClient
from mini_robot.conversation.memory import ConversationMemory
from mini_robot.conversation.semantic_memory import SemanticMemory
from mini_robot.conversation.reflection_models import ReflectionResult
import logging
from mini_robot.personality.interests import (
    RobotInterest,
    RobotInterestStore,
)
from mini_robot.personality.interest_reflection import (
    InterestReflectionResult,
)


logger = logging.getLogger(__name__)

class ReflectionEngine:

    def __init__(
        self,
        llm: LLMClient,
        conversation_memory: ConversationMemory,
        semantic_memory: SemanticMemory,
        interest_store: RobotInterestStore | None = None,
    ):
        self.llm = llm
        self.conversation_memory = conversation_memory
        self.semantic_memory = semantic_memory
        self.interest_store = interest_store

    def reflect(self, conversation_id: int) -> ReflectionResult | None:
        history = self.conversation_memory.get_unreviewed_messages(
            conversation_id,
            limit=20,
        )

        user_id = self.conversation_memory.get_conversation_user(
            conversation_id
        )

        if user_id is None:
            logger.info(
                "Skipping reflection: no identified user"
            )
            return None

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
                    "Every memory must be a complete, meaningful sentence. "
                    "Never store isolated names, single words, or vague fragments. "
                    "Do not create memories that duplicate existing information, "
                    "even if the wording differs. "
                    "Only retain information likely to be useful in future conversations. "
                    "Classify memories carefully. "
                    "Use subject='user' for facts about the identified human. "
                    "Use subject='robot' only for facts about the robot itself. "
                    "Use subject='world' only for general knowledge independent "
                    "of any particular user. "
                    "Never store a person's name, interests, preferences or "
                    "experiences as a robot or world memory. "
                    "Never infer the robot's interests from the user's interests. "

                    """
                    IDENTITY AND MEMORY RULES:

                    The current user's identity is managed externally by the server.

                    Never create memories about:
                    - The user's name or identity.
                    - A change or correction to the user's identity.
                    - Conflicting statements about who the user is.
                    - The robot's guesses about the user's identity.

                    Never treat statements made by the assistant as evidence
                    of a user's personal facts, interests, or preferences.

                    Only extract personal facts explicitly stated by the human user.

                    If an identity statement appears in the conversation,
                    ignore it for memory extraction.

                    Do not infer additional preferences or personal details
                    from the assistant's suggestions or questions.
                    """

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

        interest_result = self.reflect_interests(
            conversation_text=conversation_text,
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

        if interest_result is not None:
            self.apply_interest_reflection(interest_result)

            logger.info(
                "Interest reflection: %s (%d updates, %d new)",
                interest_result.summary,
                len(interest_result.updates),
                len(interest_result.new_interests),
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


    def reflect_interests(
        self,
        conversation_text: str,
    ) -> InterestReflectionResult | None:
        """Propose changes to the robot's developing interests."""

        if self.interest_store is None:
            return None

        interests = self.interest_store.get_all()

        existing_topics = "\n".join(
            f"- {i.topic}: "
            f"enthusiasm={i.enthusiasm:.2f}, "
            f"curiosity={i.curiosity:.2f}"
            for i in interests
        )

        messages = [
            {
                "role": "system",
                "content": """
                You are reviewing the developing interests of a small robot.

                The robot has a stable core personality, but its interests
                can evolve gradually through conversations.

                Review the conversation and propose small changes to
                the robot's interests.

                RULES:

                1. Interests belong to the ROBOT, not the human user.

                2. Do not automatically copy the user's interests.

                3. Only propose changes when the conversation gives
                a meaningful reason for the robot to become more
                or less interested in a topic.

                4. Changes should be small, normally between
                -0.05 and +0.05.

                5. A new interest should be a broad, reusable topic,
                not a fact about a particular person.

                6. Never include names, private details, or personal
                information in robot interests.

                7. Do not create interests based solely on things
                the assistant suggested or claimed.

                8. Avoid duplicating existing interests under
                different names.

                9. If nothing meaningful has changed, return
                empty updates and new_interests lists.

                10. Prefer at most two updates and one new interest
                    per reflection cycle.

                11. The robot should not become enthusiastic about
                    every topic it encounters.

                12. Changes must not alter the robot's core values,
                    identity, or behavioural principles.

                Return a structured InterestReflectionResult.
                """,
            },
            {
                "role": "user",
                "content": (
                    f"CURRENT ROBOT INTERESTS:\n"
                    f"{existing_topics or '(none)'}\n\n"
                    f"RECENT CONVERSATION:\n"
                    f"{conversation_text}"
                ),
            },
        ]

        return self.llm.generate_structured(
            messages=messages,
            response_model=InterestReflectionResult,
            max_tokens=2000,
            temperature=0.2,
        )



    def apply_interest_reflection(
        self,
        result: InterestReflectionResult | None,
    ):
        if result is None or self.interest_store is None:
            return

        # Build an authoritative mapping of existing topics.
        existing = {
            i.topic.casefold(): i.topic
            for i in self.interest_store.get_all()
        }

        # Prevent duplicate updates to the same topic.
        updated_topics = set()

        for update in result.updates[:2]:
            key = update.topic.strip().casefold()

            if key not in existing or key in updated_topics:
                continue

            updated_topics.add(key)

            topic = existing[key]

            # Enforce limits in Python as well as Pydantic.
            enthusiasm_change = max(
                -0.05, min(0.05, update.enthusiasm_change)
            )
            curiosity_change = max(
                -0.05, min(0.05, update.curiosity_change)
            )

            self.interest_store.update(
                topic,
                enthusiasm_change=enthusiasm_change,
                curiosity_change=curiosity_change,
            )

            logger.info(
                "ROBOT INTEREST UPDATED: %s "
                "(enthusiasm %+0.2f, curiosity %+0.2f): %s",
                topic,
                enthusiasm_change,
                curiosity_change,
                update.reason,
            )

        # Allow at most one new interest per reflection.
        for proposal in result.new_interests[:1]:
            topic = proposal.topic.strip()

            if not topic or len(topic) > 80:
                continue

            if topic.casefold() in existing:
                continue

            self.interest_store.add(
                RobotInterest(
                    topic=topic,
                    enthusiasm=min(0.6, proposal.enthusiasm),
                    curiosity=min(0.7, proposal.curiosity),
                    description=proposal.description[:200],
                )
            )

            logger.info(
                "NEW ROBOT INTEREST: %s",
                topic,
            )
