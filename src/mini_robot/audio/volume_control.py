import numpy as np

class VolumeController:
    def __init__(self, volume: float = 0.6):
        self.volume = volume

    def up(self):
        self.volume = min(1.0, self.volume + 0.1)

    def down(self):
        self.volume = max(0.0, self.volume - 0.1)

    def mute(self):
        self.volume = 0.0

    def apply(self, audio: np.ndarray) -> np.ndarray:
        return audio * self.volume