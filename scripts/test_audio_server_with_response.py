
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

import mini_robot.config as config


HOST = "0.0.0.0"
PORT = 8765

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONALITY_FILE = PROJECT_ROOT / "data" / config.PERSONALITY


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Initialise audio, personality and LLM
# ---------------------------------------------------------

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

# Shared by conversation and reflection.
llm_lock = threading.Lock()


# ---------------------------------------------------------
# Initialise persistent memory
# ---------------------------------------------------------

print("Initialising conversation memory...")

memory = ConversationMemory()
conversation = ConversationManager(memory)

print(f"Conversation ID: {conversation.conversation_id}")
print(f"Memory database: {memory.db_path}")


# ---------------------------------------------------------
# Initialise background reflection
# ---------------------------------------------------------

reflection_engine = ReflectionEngine(
    llm=llm,
    conversation_memory=memory,
    semantic_memory=conversation.semantic_memory,
)

reflection_worker = ReflectionWorker(
    engine=reflection_engine,
    conversation_id=conversation.conversation_id,
    llm_lock=llm_lock,
    interval=30.0,
)


# ---------------------------------------------------------
# LLM generation
# ---------------------------------------------------------

def generate_response(messages):
    # This runs in a worker thread, not the asyncio event loop.
    with llm_lock:
        return llm.generate_structured(
            messages=messages,
            response_model=RobotResponse,
            max_tokens=400,
        )


# ---------------------------------------------------------
# WebSocket server
# ---------------------------------------------------------

async def handle_client(websocket):
    print("\nPi connected")

    try:
        async for message in websocket:

            if not isinstance(message, bytes):
                await websocket.send(
                    json.dumps({
                        "error": "Expected binary PCM audio"
                    })
                )
                continue

            # ---------------------------------------------
            # 1. Transcribe audio
            # ---------------------------------------------

            start = time.perf_counter()

            transcription = await asyncio.to_thread(
                stt.transcribe_pcm,
                message,
            )

            stt_time = time.perf_counter() - start

            print(f"\nHuman: {transcription}")
            print(f"Whisper: {stt_time:.2f}s")

            if not transcription:
                await websocket.send(
                    json.dumps({
                        "text": "",
                        "response": "",
                    })
                )
                continue

            # ---------------------------------------------
            # 2. Save user message
            # ---------------------------------------------

            conversation.add_user_message(transcription)

            # ---------------------------------------------
            # 3. Build context-aware LLM messages
            # ---------------------------------------------

            messages = conversation.get_llm_messages(
                system_prompt=system_prompt
            )

            # ---------------------------------------------
            # 4. Generate structured response
            # ---------------------------------------------

            start = time.perf_counter()

            response = await asyncio.to_thread(
                generate_response,
                messages,
            )

            llm_time = time.perf_counter() - start

            # ---------------------------------------------
            # 5. Save robot response
            # ---------------------------------------------

            conversation.add_robot_response(response)

            print(f"\n{personality.name}: {response.speech}")
            print(
                f"Emotion: {response.emotion.value}, "
                f"Gesture: {response.gesture.value}"
            )
            print(f"LLM: {llm_time:.2f}s")

            # ---------------------------------------------
            # 6. Send response to Raspberry Pi
            # ---------------------------------------------

            await websocket.send(
                json.dumps({
                    "text": transcription,
                    "response": response.speech,
                    "emotion": response.emotion.value,
                    "gesture": response.gesture.value,
                    "personality": personality.name,
                    "stt_seconds": round(stt_time, 3),
                    "llm_seconds": round(llm_time, 3),
                    "processing_seconds": round(
                        stt_time + llm_time, 3
                    ),
                })
            )

    except Exception as exc:
        print(f"\nConnection error: {exc}")
        traceback.print_exc()

        try:
            await websocket.send(
                json.dumps({"error": str(exc)})
            )
        except Exception:
            pass


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

async def main():
    reflection_worker.start()

    try:
        async with serve(
            handle_client,
            HOST,
            PORT,
            max_size=10 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=120,
        ):
            print(
                f"\nMini Robot server listening on "
                f"{HOST}:{PORT}"
            )
            print(f"Active personality: {personality.name}")
            print("Persistent memory: enabled")
            print("Background reflection: every 30 seconds")

            await asyncio.Future()

    finally:
        print("\nStopping reflection worker...")
        await asyncio.to_thread(reflection_worker.stop)

        conversation.close()

        print("Server stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested.")
