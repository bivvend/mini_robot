from pathlib import Path

from mini_robot.audio.text_to_speech import PiperTTS


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    PROJECT_ROOT
    / "data"
    / "voices"
    / "en_GB-alan-medium.onnx"
)

OUTPUT_PATH = PROJECT_ROOT / "test_speech.wav"


def main():
    tts = PiperTTS(MODEL_PATH)

    text = (
        "Hello! I'm Mochi, your tiny robot companion. "
        "I can finally speak! Isn't that exciting?"
    )

    print("Generating speech...")
    tts.synthesize(text, OUTPUT_PATH)

    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()