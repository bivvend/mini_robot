import re
from dataclasses import dataclass


@dataclass
class RobotCommand:
    name: str
    argument: str | None = None


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
    "web_search": [
        r"\b(?:search for|search the web for|web lookup)\s+(.+)",
    ],
}


def detect_command(text: str) -> RobotCommand | None:
    for name, patterns in COMMANDS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                argument = (
                    match.group(1).strip().rstrip(".?!")
                    if match.lastindex
                    else None
                )

                return RobotCommand(
                    name=name,
                    argument=argument,
                )

    return None