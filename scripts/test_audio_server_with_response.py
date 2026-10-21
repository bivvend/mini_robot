import asyncio
import json
import logging
import threading
import time
import traceback
from pathlib import Path

from websockets.asyncio.server import serve

from mini_robot.audio.speech_to_text import WhisperSTT
from mini_robot.llm.client import LLMClient
from mini_robot.llm.models import RobotResponse
from mini_robot.personality.personality import RobotPersonality
from mini_robot.personality.engine import build_personality_prompt
from mini_robot.conversation.memory import ConversationMemory
from mini_robot.conversation.manager import ConversationManager
from mini_robot.conversation.reflection import ReflectionEngine
from mini_robot.conversation.reflection_worker import ReflectionWorker
from mini_robot.conversation.user_detector import UserDetector
import mini_robot.config as config

HOST = "0.0.0.0"
PORT = 8765
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONALITY_FILE = PROJECT_ROOT / "data" / config.PERSONALITY



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

print("Loading Whisper...")
stt = WhisperSTT(model_name="base.en")

print("Loading personality...")
personality = RobotPersonality.model_validate_json(
    PERSONALITY_FILE.read_text(encoding="utf-8")
)
system_prompt = build_personality_prompt(personality)
print(f"Personality: {personality.name}")

print("Initialising LLM...")
llm = LLMClient()
llm_lock = threading.Lock()

print("Initialising conversation memory...")
memory = ConversationMemory()
print(f"Memory database: {memory.db_path}")

from mini_robot.conversation.user_detector import UserDetector

user_detector = UserDetector(
    robot_names=config.ROBOT_NAMES
)
current_user = None
conversation = None
reflection_worker = None
# One robot has one active user. Serialize handling across all connections.
request_lock = asyncio.Lock()


def generate_response(messages):
    with llm_lock:
        return llm.generate_structured(
            messages=messages,
            response_model=RobotResponse,
            max_tokens=400,
        )



def start_user_session(user_name: str):
    """Create user-scoped conversation and reflection worker."""

    # Retrieve existing user or register a new one
    user_id = memory.get_or_create_user(user_name)

    logger.info(
        "Starting session for %s (user_id=%d)",
        user_name,
        user_id,
    )

    new_conversation = ConversationManager(
        memory,
        user_id=user_id,
    )

    if new_conversation.user_id != user_id:
        new_conversation.close()
        raise RuntimeError(
            f"Conversation user mismatch: expected {user_id}, "
            f"got {new_conversation.user_id}"
        )

    engine = ReflectionEngine(
        llm=llm,
        conversation_memory=memory,
        semantic_memory=new_conversation.semantic_memory,
    )

    worker = ReflectionWorker(
        engine=engine,
        conversation_id=new_conversation.conversation_id,
        llm_lock=llm_lock,
        interval=30.0,
    )

    worker.start()

    return new_conversation, worker


def build_session_prompt():
    prompt = system_prompt

    if current_user is None:
        identity = (
            "CURRENT USER: Unknown.\n"
            "Do not assume the user's identity."
        )
    else:
        identity = (
            f"CURRENT USER: {current_user}.\n"
            "This identity has been established by the server.\n"
            "It is authoritative and overrides conversation history "
            "and stored memories.\n"
            "Do not infer or change the user's identity from dialogue.\n"
            "Only the server can switch users."
        )

    return identity + "\n\n" + prompt

async def switch_user(name):
    global current_user
    global conversation
    global reflection_worker

    user_id = memory.get_or_create_user(name)

    if current_user == user_id:
        return

    logger.info(
        "Switching user: %s -> %s",
        current_user,
        name,
    )

    if reflection_worker is not None:
        await asyncio.to_thread(reflection_worker.stop)
        reflection_worker = None

    if conversation is not None:
        conversation.close()
        conversation = None


    conversation, reflection_worker = start_user_session(name) 

    reflection_worker.start()

    current_user = user_id

    logger.info(
        "Active user: %s (ID %d)",
        name,
        user_id,
    )



async def handle_client(websocket):
    logger.info("Pi connected")
    try:
        async for message in websocket:
            if not isinstance(message, bytes):
                await websocket.send(json.dumps({"error": "Expected binary PCM audio"}))
                continue

            async with request_lock:
                start = time.perf_counter()
                transcription = await asyncio.to_thread(stt.transcribe_pcm, message)
                stt_time = time.perf_counter() - start
                logger.info("Human: %s", transcription)
                logger.info("Whisper: %.2fs", stt_time)

                if not transcription:
                    await websocket.send(json.dumps({
                        "text": "", "response": "",
                        "user": current_user,
                        "memory_enabled": current_user is not None,
                    }))
                    continue

                detected_user = user_detector.detect(transcription)
                if detected_user is not None:
                    await switch_user(detected_user)

                if conversation is None:
                    # Anonymous: no DB writes, no reflection, no personal retrieval.
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": transcription},
                    ]
                else:
                    conversation.add_user_message(transcription)
                    messages = conversation.get_llm_messages(
                        system_prompt=build_session_prompt()
                    )

                start = time.perf_counter()
                response = await asyncio.to_thread(generate_response, messages)
                llm_time = time.perf_counter() - start

                if conversation is not None:
                    conversation.add_robot_response(response)

                logger.info("%s: %s", personality.name, response.speech)
                logger.info("Emotion: %s, Gesture: %s",
                            response.emotion.value, response.gesture.value)
                logger.info("LLM: %.2fs", llm_time)

                await websocket.send(json.dumps({
                    "text": transcription,
                    "response": response.speech,
                    "emotion": response.emotion.value,
                    "gesture": response.gesture.value,
                    "personality": personality.name,
                    "user": current_user,
                    "memory_enabled": current_user is not None,
                    "stt_seconds": round(stt_time, 3),
                    "llm_seconds": round(llm_time, 3),
                    "processing_seconds": round(stt_time + llm_time, 3),
                }))
    except Exception as exc:
        logger.exception("Connection error: %s", exc)
        try:
            await websocket.send(json.dumps({"error": str(exc)}))
        except Exception:
            pass


async def main():
    try:
        async with serve(
            handle_client,
            HOST,
            PORT,
            max_size=10 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=120,
        ):
            print(f"\nMini Robot server listening on {HOST}:{PORT}")
            print(f"Active personality: {personality.name}")
            print("Current user: unassigned")
            print("Persistent memory and reflection: awaiting identification")
            await asyncio.Future()
    finally:
        print("\nStopping server...")
        if reflection_worker is not None:
            await asyncio.to_thread(reflection_worker.stop)
        if conversation is not None:
            conversation.close()
        print("Server stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested.")
