import asyncio
import json
import os
import time

from openai import OpenAI
from websockets.asyncio.server import serve

from mini_robot.audio.speech_to_text import WhisperSTT


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

HOST = "0.0.0.0"
PORT = 8765

LLM_BASE_URL = os.getenv(
    "MINI_ROBOT_LLM_URL",
    "http://127.0.0.1:8000/v1",
)

LLM_MODEL = os.getenv(
    "MINI_ROBOT_LLM_MODEL",
    "local-model",
)

SYSTEM_PROMPT = """
You are Mini, a friendly, curious little desktop robot.

You have a playful personality and enjoy chatting with humans.

Keep your replies conversational and fairly short,
usually one or two sentences.

You are speaking aloud, so avoid markdown formatting,
lists, or long explanations.
"""


# ---------------------------------------------------------
# Initialise models
# ---------------------------------------------------------

stt = WhisperSTT(model_name="base.en")

llm = OpenAI(
    base_url=LLM_BASE_URL,
    api_key="not-needed",
)


def generate_response(history):
    response = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=history,
        temperature=0.8,
        max_tokens=150,
    )

    return response.choices[0].message.content or ""


# ---------------------------------------------------------
# WebSocket server
# ---------------------------------------------------------

async def handle_client(websocket):
    print("Pi connected")

    history = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    try:
        async for message in websocket:

            if not isinstance(message, bytes):
                await websocket.send(
                    json.dumps({"error": "Expected binary PCM audio"})
                )
                continue

            # 1. Speech to text
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

            # 2. Generate LLM response
            history.append({
                "role": "user",
                "content": transcription,
            })

            start = time.perf_counter()

            reply = await asyncio.to_thread(
                generate_response,
                history.copy(),
            )

            llm_time = time.perf_counter() - start

            history.append({
                "role": "assistant",
                "content": reply,
            })

            print(f"Mini: {reply}")
            print(f"LLM: {llm_time:.2f}s")

            # 3. Return response to Raspberry Pi
            await websocket.send(
                json.dumps({
                    "text": transcription,
                    "response": reply,
                    "stt_seconds": round(stt_time, 3),
                    "llm_seconds": round(llm_time, 3),
                    "processing_seconds": round(
                        stt_time + llm_time, 3
                    ),
                })
            )

    except Exception as exc:
        print(f"Connection ended: {exc}")


async def main():
    async with serve(
        handle_client,
        HOST,
        PORT,
        max_size=10 * 1024 * 1024,
    ):
        print(f"Mini Robot conversation server: {HOST}:{PORT}")
        print(f"LLM endpoint: {LLM_BASE_URL}")
        print(f"LLM model: {LLM_MODEL}")

        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())