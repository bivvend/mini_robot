#RUNS ON RPi
import sounddevice as sd
import numpy as np


def record_audio(
    duration: float = 5.0,
    sample_rate: int = 16000,
    device=None,
) -> np.ndarray:
    """Record mono 16-bit PCM audio from the microphone."""

    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        device=device,
    )
    sd.wait()

    return audio.reshape(-1)