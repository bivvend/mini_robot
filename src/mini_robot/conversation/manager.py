
from mini_robot.conversation.memory import ConversationMemory
from mini_robot.conversation.semantic_memory import SemanticMemory
from mini_robot.llm.models import RobotResponse
from mini_robot.conversation.context import ContextManager


class ConversationManager:

    def __init__(
        self,
        memory: ConversationMemory,
        conversation_id: int | None = None,

    ):
        self.memory = memory

        self.semantic_memory = SemanticMemory(
                db_path=self.memory.db_path
        )

        self.conversation_id = (
            conversation_id
            if conversation_id is not None
            else self.memory.start_conversation()
        )

        self.context = ContextManager(
            memory=self.memory,
            semantic_memory=self.semantic_memory,
        )

    def add_user_message(self, text: str):
        self.memory.add_message(
            conversation_id=self.conversation_id,
            role="user",
            content=text,
        )

    def add_robot_response(self, response: RobotResponse):
        self.memory.add_message(
            conversation_id=self.conversation_id,
            role="assistant",
            content=response.speech,
            emotion=response.emotion.value,
            gesture=response.gesture.value,
        )

    def get_llm_messages(self, system_prompt: str) -> list[dict[str, str]]:
        return self.context.build_messages(
        conversation_id=self.conversation_id,
        system_prompt=system_prompt,
        )

    def close(self):
        self.memory.end_conversation(self.conversation_id)
