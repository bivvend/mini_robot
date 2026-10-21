
import re


class UserDetector:
    def __init__(self, robot_names: list[str]):

        if not robot_names:
            raise ValueError("At least one robot name is required")

        names = {
            name.strip()
            for name in robot_names
            if name.strip()
        }

        name_pattern = "|".join(
            re.escape(name)
            for name in sorted(names, key=len, reverse=True)
        )

        introduction_pattern = (
            r"(?:i['’]?m|i\s+am|my\s+name\s+is|"
            r"this\s+is|it['’]s|it\s+is)"
        )

        self.pattern = re.compile(
            rf"^\s*(?:hi|hello|hey)\s+"
            rf"(?:{name_pattern})"
            rf"\s*[,!.]?\s*"
            rf"{introduction_pattern}\s+"
            rf"(?P<name>[a-z][a-z'-]*)\b",
            flags=re.IGNORECASE,
        )

        self.invalid_names = {
            "fine", "good", "okay", "ok",
            "here", "back", "ready",
            "happy", "tired", "sorry",
        }

    def detect(self, text: str) -> str | None:
        """Return the introduced user's name, or None."""

        match = self.pattern.search(text.strip())

        if match is None:
            return None

        name = match.group("name").capitalize()

        if name.lower() in self.invalid_names:
            return None

        return name
