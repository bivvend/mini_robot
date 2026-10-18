import time
from faster_whisper import WhisperModel

model = WhisperModel(
    "base.en",
    device="cpu",
    compute_type="int8"
)

for filename in ["test.wav", "normalised.wav"]:
    
    start = time.perf_counter()

    segments, info = model.transcribe(
        filename,
        language="en",
        beam_size=5
    )

    text = " ".join(s.text.strip() for s in segments)

    elapsed = time.perf_counter() - start

    print(f"\nFile: {filename}")
    print(f"Recognised: {text}")
    print(f"Transcription time: {elapsed:.2f} seconds")