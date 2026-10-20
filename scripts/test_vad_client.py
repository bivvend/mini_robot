import argparse
import asyncio
import json
import queue

import sounddevice as sd
from websockets.asyncio.client import connect

from mini_robot.audio.voice_activity import VoiceActivityDetector
from mini_robot.audio.text_to_speech import prepare_speech_text

import io
import wave
from pathlib import Path

import soundfile as sf

from mini_robot.audio.text_to_speech import PiperTTS

def speak(tts: PiperTTS, text: str):
    """Generate speech with Piper and play it through the speakers."""

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:
        tts.voice.synthesize_wav(text, wav_file)

    buffer.seek(0)

    audio, sample_rate = sf.read(buffer, dtype="float32")

    print(f"Speaking ({len(audio) / sample_rate:.1f}s)")

    sd.play(audio, samplerate=sample_rate)
    sd.wait()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--device", type=int, default=None)
    args = parser.parse_args()

    vad = VoiceActivityDetector()
    audio_queue = queue.Queue(maxsize=100)

    project_root = Path(__file__).resolve().parent.parent

    voice_path = (
        project_root
        / "data"
        / "voices"
        / "models_en_US-seira-medium.onnx"
    )

    print("Loading Piper voice...")
    tts = PiperTTS(voice_path)

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

                reply = response.get("response", "")

                if reply:
                    print(f"Mini: {reply}")
                    print(
                        f"Emotion: {response.get('emotion')}, "
                        f"Gesture: {response.get('gesture')}"
                    )

                    # Run TTS without blocking the asyncio event loop
                    speech_text = prepare_speech_text(reply)

                    if speech_text:
                        await asyncio.to_thread(speak, tts, speech_text)

                # Discard audio collected during response generation and playback
                while not audio_queue.empty():
                    try:
                        audio_queue.get_nowait()
                    except queue.Empty:
                        break

                vad.reset()
                print("Listening...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")