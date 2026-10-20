import asyncio
import json
import time
import traceback
from pathlib import Path

from websockets.asyncio.server import serve

from mini_robot.audio.speech_to_text import WhisperSTT
from mini_robot.llm.client import LLMClient
from mini_robot.llm.models import RobotResponse
from mini_robot.personality.personality import RobotPersonality
from mini_robot.personality.engine import build_personality_prompt
import mini_robot.config as config


HOST = "0.0.0.0"
PORT = 8765

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONALITY_FILE = PROJECT_ROOT / "data" / config.PERSONALITY


# ---------------------------------------------------------
# Initialise Whisper and the existing personality system
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


def generate_response(messages):
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

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    try:
        async for message in websocket:

            if not isinstance(message, bytes):
                await websocket.send(
                    json.dumps({
                        "error": "Expected binary PCM audio"
                    })
                )
                continue

            # 1. Transcribe audio
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

            # 2. Send transcription to personality-driven LLM
            user_message = {
                "role": "user",
                "content": transcription,
            }

            messages.append(user_message)

            start = time.perf_counter()

            try:
                response = await asyncio.to_thread(
                    generate_response,
                    messages.copy(),
                )
            except Exception:
                messages.pop()
                raise

            llm_time = time.perf_counter() - start

            # Preserve structured response in conversation history
            messages.append({
                "role": "assistant",
                "content": response.model_dump_json(),
            })

            print(f"\n{personality.name}: {response.speech}")
            print(
                f"Emotion: {response.emotion.value}, "
                f"Gesture: {response.gesture.value}"
            )
            print(f"LLM: {llm_time:.2f}s")

            # 3. Send response to Pi
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
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())