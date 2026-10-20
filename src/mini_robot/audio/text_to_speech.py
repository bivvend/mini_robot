from pathlib import Path
import wave
import emoji

from piper import PiperVoice


def prepare_speech_text(text: str) -> str:
    """Remove emojis from text before speech synthesis."""
    text = emoji.replace_emoji(text, replace="")
    return " ".join(text.split())

class PiperTTS:
    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path)
        self.voice = PiperVoice.load(str(self.model_path))

    def synthesize(self, text: str, output_path: str | Path):
        output_path = Path(output_path)

        with wave.open(str(output_path), "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file)

        return output_path