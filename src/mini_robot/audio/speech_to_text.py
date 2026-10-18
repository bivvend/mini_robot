#RUNS ON DESKTOP
import numpy as np
from faster_whisper import WhisperModel


class WhisperSTT:
    def __init__(self, model_name="base.en"):
        self.model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
        )

    def transcribe_pcm(self, pcm: bytes) -> str:
        """Transcribe 16 kHz mono signed 16-bit PCM audio."""

        audio = np.frombuffer(pcm, dtype="<i2")
        audio = audio.astype(np.float32) / 32768.0

        segments, _ = self.model.transcribe(
            audio,
            language="en",
            beam_size=5,
        )

        return " ".join(
            segment.text.strip() for segment in segments
        ).strip()