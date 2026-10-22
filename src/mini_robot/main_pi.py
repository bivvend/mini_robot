"""Mini Robot Raspberry Pi audio client.

Run with: python -m mini_robot.main_pi --host 192.168.1.10
"""

import argparse
import asyncio
import io
import json
import logging
import queue
import wave
from pathlib import Path

import sounddevice as sd
import soundfile as sf
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from mini_robot.audio.voice_activity import VoiceActivityDetector
from mini_robot.audio.text_to_speech import PiperTTS, prepare_speech_text
from mini_robot.audio.volume_control import VolumeController

LOGGER = logging.getLogger(__name__)
SAMPLE_RATE = 16_000
BLOCK_SIZE = 512
DEFAULT_PORT = 8765


class MiniRobotPiClient:
    def __init__(self, host: str, port: int, device: int | None, voice_path: Path):
        self.uri = f"ws://{host}:{port}"
        self.device = device
        self.vad = VoiceActivityDetector()
        self.audio_queue: queue.Queue = queue.Queue(maxsize=100)
        self.volume = VolumeController()
        LOGGER.info("Loading Piper voice: %s", voice_path)
        self.tts = PiperTTS(voice_path)

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            LOGGER.warning("Audio input: %s", status)
        try:
            self.audio_queue.put_nowait(indata.copy())
        except queue.Full:
            # Keep the real-time audio callback nonblocking.
            pass

    def handle_command(self, command: dict):
        name = command.get("name")
        match name:
            case "volume_up":
                self.volume.up()
            case "volume_down":
                self.volume.down()
            case "mute":
                self.volume.mute()
            case _:
                LOGGER.warning("Unknown command: %r", name)
                return
        LOGGER.info("Executed command: %s", name)

    def speak(self, text: str):
        """Synchronous synthesis and playback; run using asyncio.to_thread."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            self.tts.voice.synthesize_wav(text, wav_file)
        buffer.seek(0)
        audio, sample_rate = sf.read(buffer, dtype="float32")
        audio = self.volume.apply(audio)
        LOGGER.info("Speaking (%.1fs)", len(audio) / sample_rate)
        sd.play(audio, samplerate=sample_rate)
        sd.wait()

    def clear_audio(self):
        while True:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        self.vad.reset()

    async def next_audio_chunk(self):
        """Wait for microphone input without blocking cancellation."""
        while True:
            try:
                return self.audio_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.01)

    async def handle_response(self, response: dict):
        if "error" in response:
            LOGGER.error("Server error: %s", response["error"])
            return

        if response.get("type") == "command":
            self.handle_command(response)
            return

        reply = response.get("response", "")
        if not reply:
            return

        LOGGER.info("Mini: %s", reply)
        LOGGER.info("Emotion: %s, Gesture: %s", response.get("emotion"), response.get("gesture"))
        speech_text = prepare_speech_text(reply)
        if speech_text:
            await asyncio.to_thread(self.speak, speech_text)

    async def run(self):
        LOGGER.info("Connecting to %s", self.uri)
        async with connect(
            self.uri,
            max_size=10 * 1024 * 1024,
            ping_timeout=120,
        ) as websocket:
            LOGGER.info("Connected. Speak naturally. Ctrl+C to exit.")
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=BLOCK_SIZE,
                device=self.device,
                callback=self.audio_callback,
            ):
                try:
                    while True:
                        chunk = await self.next_audio_chunk()
                        audio = self.vad.process(chunk)
                        if audio is None:
                            continue

                        LOGGER.info("Sending %.2fs of speech", len(audio) / SAMPLE_RATE)
                        try:
                            await websocket.send(audio.astype("<i2").tobytes())
                            response = json.loads(await websocket.recv())
                            await self.handle_response(response)
                        finally:
                            # Ignore mic input captured while waiting or speaking.
                            self.clear_audio()
                            LOGGER.info("Listening...")
                finally:
                    sd.stop()


def default_voice_path() -> Path:
    # With src/mini_robot/main_pi.py, parents[2] is the repository root.
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "data" / "voices" / "en_GB-alan-medium.onnx"


def main():
    parser = argparse.ArgumentParser(description="Mini Robot Raspberry Pi audio client")
    parser.add_argument("--host", required=True, help="PC server IP address or hostname")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--device", type=int, default=None, help="Input audio device index")
    parser.add_argument("--voice", type=Path, default=default_voice_path(), help="Piper ONNX voice path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
    if not args.voice.is_file():
        parser.error(f"Piper voice not found: {args.voice} (use --voice to specify it)")

    client = MiniRobotPiClient(args.host, args.port, args.device, args.voice)
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        LOGGER.info("Stopped")
    except (OSError, ConnectionClosed) as exc:
        LOGGER.error("Connection/audio error: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
