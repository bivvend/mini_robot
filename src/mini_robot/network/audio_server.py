import asyncio
import json
import time

from websockets.asyncio.server import serve

from mini_robot.audio.speech_to_text import WhisperSTT


async def run_server(host="0.0.0.0", port=8765):
    stt = WhisperSTT(model_name="base.en")

    async def handle_client(websocket):
        print("Pi connected")

        try:
            async for message in websocket:
                if not isinstance(message, bytes):
                    await websocket.send(
                        json.dumps({"error": "Expected binary PCM audio"})
                    )
                    continue

                print(f"Received {len(message)} audio bytes")

                start = time.perf_counter()
                text = await asyncio.to_thread(
                    stt.transcribe_pcm, message
                )
                elapsed = time.perf_counter() - start

                print(f"Recognised: {text}")
                print(f"Transcription: {elapsed:.2f}s")

                await websocket.send(
                    json.dumps({
                        "text": text,
                        "processing_seconds": round(elapsed, 3),
                    })
                )

        except Exception as exc:
            print(f"Connection ended: {exc}")

    async with serve(
        handle_client,
        host,
        port,
        max_size=10 * 1024 * 1024,
    ):
        print(f"Audio server listening on {host}:{port}")
        await asyncio.Future()