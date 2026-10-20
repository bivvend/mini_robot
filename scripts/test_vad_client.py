import argparse
import asyncio
import json
import queue

import sounddevice as sd
from websockets.asyncio.client import connect

from mini_robot.audio.voice_activity import VoiceActivityDetector


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--device", type=int, default=None)
    args = parser.parse_args()

    vad = VoiceActivityDetector()
    audio_queue = queue.Queue(maxsize=100)

    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status)

        try:
            audio_queue.put_nowait(indata.copy())
        except queue.Full:
            pass

    uri = f"ws://{args.host}:{args.port}"

    print(f"Connecting to {uri}")

    async with connect(
        uri,
        max_size=10 * 1024 * 1024,
        ping_timeout=120,
    ) as websocket:

        print("Connected. Speak naturally. Ctrl+C to exit.")

        with sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="int16",
            blocksize=512,
            device=args.device,
            callback=audio_callback,
        ):
            while True:
                chunk = await asyncio.to_thread(audio_queue.get)

                audio = vad.process(chunk)

                if audio is None:
                    continue

                duration = len(audio) / 16000
                print(f"Sending {duration:.2f}s of speech...")

                await websocket.send(audio.astype("<i2").tobytes())

                response = json.loads(await websocket.recv())

                if "error" in response:
                    print(f"Server error: {response['error']}")
                    continue

                print(f"\nYou: {response.get('text', '')}")

                if response.get("response"):
                    print(f"Mini: {response['response']}")
                    print(
                        f"Emotion: {response.get('emotion')}, "
                        f"Gesture: {response.get('gesture')}"
                    )

                print("\nListening...")

                # Discard audio captured while the LLM was responding.
                while not audio_queue.empty():
                    try:
                        audio_queue.get_nowait()
                    except queue.Empty:
                        break

                vad.reset()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")