from collections import deque

import numpy as np
from silero_vad import load_silero_vad, VADIterator


class VoiceActivityDetector:
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 512

    def __init__(
        self,
        threshold=0.5,
        silence_ms=700,
        pre_speech_ms=300,
        max_speech_seconds=15,
    ):
        self.model = load_silero_vad(onnx=True)

        self.vad = VADIterator(
            self.model,
            threshold=threshold,
            sampling_rate=self.SAMPLE_RATE,
            min_silence_duration_ms=silence_ms,
            speech_pad_ms=0,
        )

        pre_chunks = max(
            1,
            round(pre_speech_ms * self.SAMPLE_RATE /
                  (1000 * self.CHUNK_SIZE))
        )

        self.pre_buffer = deque(maxlen=pre_chunks)
        self.max_chunks = int(
            max_speech_seconds * self.SAMPLE_RATE /
            self.CHUNK_SIZE
        )

        self.recording = False
        self.chunks = []

    def process(self, chunk):
        """Return completed int16 PCM audio, or None."""

        chunk = np.asarray(chunk, dtype=np.int16).reshape(-1)

        if len(chunk) != self.CHUNK_SIZE:
            raise ValueError("Expected 512 audio samples")

        # Silero expects float32 samples in [-1, 1].
        samples = chunk.astype(np.float32) / 32768.0

        event = self.vad(samples, return_seconds=False)

        if not self.recording:
            self.pre_buffer.append(chunk.copy())

            if event and "start" in event:
                self.recording = True
                self.chunks = list(self.pre_buffer)
                self.pre_buffer.clear()
                print("Speech detected")

            return None

        self.chunks.append(chunk.copy())

        finished = event and "end" in event
        too_long = len(self.chunks) >= self.max_chunks

        if finished or too_long:
            audio = np.concatenate(self.chunks)

            print("Speech ended" if finished else "Maximum duration")

            self.reset()
            return audio

        return None

    def reset(self):
        self.recording = False
        self.chunks = []
        self.pre_buffer.clear()
        self.vad.reset_states()