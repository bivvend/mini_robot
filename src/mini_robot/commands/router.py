import re
from dataclasses import dataclass


@dataclass
class RobotCommand:
    name: str
    value: int | None = None


COMMANDS = {
    "volume_up": [
        r"\b(?:volume up|speak louder|louder)\b",
        r"\bturn (?:the )?volume up\b",
    ],
    "volume_down": [
        r"\b(?:volume down|speak quieter|quieter)\b",
        r"\bturn (?:the )?volume down\b",
    ],
    "mute": [
        r"\b(?:mute|be quiet|stop talking)\b",
    ],
}


def detect_command(text: str) -> RobotCommand | None:
    for name, patterns in COMMANDS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return RobotCommand(name=name)

    return None