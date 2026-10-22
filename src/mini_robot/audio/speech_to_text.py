#RUNS ON DESKTOP
import numpy as np
from faster_whisper import WhisperModel
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    avg_logprob: float
    no_speech_prob: float
    compression_ratio: float

class WhisperSTT:
    def __init__(self, model_name="base.en"):
        self.model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
        )

    def transcribe_pcm(self, pcm_bytes: bytes) -> TranscriptionResult:

        # Convert raw 16-bit PCM to floating-point audio
        audio = np.frombuffer(
            pcm_bytes, dtype="<i2"
        ).astype(np.float32) / 32768.0

        # Normalise audio, limiting maximum gain
        peak = np.max(np.abs(audio)) if len(audio) else 0.0

        if peak > 0.01:
            gain = min(0.8 / peak, 5.0)
            audio = np.clip(audio * gain, -1.0, 1.0)

        print(f"Audio peak: {peak:.4f}")

        # Transcribe the NumPy audio array
        segments, info = self.model.transcribe(
            audio,
            language="en",
        )

        segments = list(segments)

        if not segments:
            return TranscriptionResult(
                text="",
                avg_logprob=-10.0,
                no_speech_prob=1.0,
                compression_ratio=0.0,
            )

        text = " ".join(s.text.strip() for s in segments).strip()

        return TranscriptionResult(
            text=text,
            avg_logprob=min(s.avg_logprob for s in segments),
            no_speech_prob=max(s.no_speech_prob for s in segments),
            compression_ratio=max(s.compression_ratio for s in segments),
        )