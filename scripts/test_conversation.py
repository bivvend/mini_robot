
from pathlib import Path

from mini_robot.config import PERSONALITY
from mini_robot.llm.client import LLMClient
from mini_robot.llm.models import RobotResponse
from mini_robot.personality.personality import RobotPersonality
from mini_robot.personality.engine import build_personality_prompt
from mini_robot.conversation.memory import ConversationMemory
from mini_robot.conversation.manager import ConversationManager
import threading
from mini_robot.conversation.reflection import ReflectionEngine
from mini_robot.conversation.reflection_worker import ReflectionWorker

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

def main():

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    PERSONALITY_FILE = PROJECT_ROOT / "data" / PERSONALITY

    personality = RobotPersonality.model_validate_json(
        Path(PERSONALITY_FILE).read_text(encoding="utf-8")
    )

    system_prompt = build_personality_prompt(personality)

    client = LLMClient()
    memory = ConversationMemory()

    conversation = ConversationManager(
        memory=memory,
    )

    llm_lock = threading.Lock()

    reflection_engine = ReflectionEngine(
        llm=client,
        conversation_memory=memory,
        semantic_memory=conversation.semantic_memory,
    )

    reflection_worker = ReflectionWorker(
        engine=reflection_engine,
        conversation_id=conversation.conversation_id,
        llm_lock=llm_lock,
        interval=30.0,
    )

    reflection_worker.start()

    print(f"Conversation ID: {conversation.conversation_id}")
    print(f"Personality: {personality.name}")
    print("Type 'exit' to quit.\n")

    try:
        while True:
            user_input = input("You: ").strip()

            if user_input.lower() in ("exit", "quit"):
                break

            if not user_input:
                continue

            conversation.add_user_message(user_input)

            messages = conversation.get_llm_messages(system_prompt)

            estimated_tokens = sum(
                conversation.context.estimate_tokens(m["content"]) + 12
                for m in messages
            )

            print(
                f"[Context: {len(messages) - 1} history messages, "
                f"~{estimated_tokens} tokens]"
            )

            with llm_lock:
                response = client.generate_structured(
                    messages=messages,
                    response_model=RobotResponse,
                    max_tokens=200,
                )

            print(messages)

            conversation.add_robot_response(response)

            print(f"\n{personality.name}: {response.speech}")
            print(
                f"[emotion={response.emotion.value}, "
                f"gesture={response.gesture.value}]\n"
            )

    finally:
        reflection_worker.stop()
        conversation.close()
        



if __name__ == "__main__":
    main()
