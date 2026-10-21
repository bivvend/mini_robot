
from itertools import product

from src.mini_robot.conversation.user_detector import UserDetector
from src.mini_robot import config


detector = UserDetector(robot_names=config.ROBOT_NAMES)

GREETINGS = ["Hi", "Hello", "Hey"]

INTRODUCTIONS = [
    "I'm",
    "I am",
    "my name is",
    "this is",
    "it's",
    "it is",
]

USER_NAMES = ["Simon", "Alice", "Bob", "Charlie"]

SEPARATORS = [", ", " ", ". ", "! "]

TEST_CASES = []


# ---------------------------------------------------------
# 1. Generate valid introductions
# ---------------------------------------------------------

for robot, greeting, introduction, user, separator in product(
    config.ROBOT_NAMES,
    GREETINGS,
    INTRODUCTIONS,
    USER_NAMES,
    SEPARATORS,
):
    transcription = (
        f"{greeting} {robot}{separator}"
        f"{introduction} {user}"
    )

    TEST_CASES.append((transcription, user))


# ---------------------------------------------------------
# 2. Case and punctuation variations
# ---------------------------------------------------------

for robot in config.ROBOT_NAMES:
    TEST_CASES.extend([
        (f"hi {robot.lower()}, i'm simon", "Simon"),
        (f"HI {robot.upper()}, I'M SIMON", "Simon"),
        (f"Hi {robot}, I’m Simon", "Simon"),
        (f"  Hi {robot}, I'm Simon  ", "Simon"),
        (f"Hi   {robot},   I'm   Simon", "Simon"),
        (f"Hi {robot}, I'm Simon.", "Simon"),
    ])


# ---------------------------------------------------------
# 3. Invalid introductions
# ---------------------------------------------------------

INVALID_NAMES = [
    "fine", "good", "okay", "ok",
    "here", "back", "ready",
    "happy", "tired", "sorry",
]

for robot, invalid in product(
    config.ROBOT_NAMES,
    INVALID_NAMES,
):
    TEST_CASES.append(
        (f"Hi {robot}, I'm {invalid}", None)
    )


# ---------------------------------------------------------
# 4. Incomplete introductions
# ---------------------------------------------------------

for robot in config.ROBOT_NAMES:
    TEST_CASES.extend([
        (f"Hi {robot}", None),
        (f"Hi {robot}, I'm", None),
        (f"Hi {robot}, I am", None),
        (f"Hi {robot}, my name is", None),
        (f"Hi {robot}, Simon", None),
        (f"Hi {robot}, how are you?", None),
        (f"Hi {robot}, I'm 123", None),
    ])


# ---------------------------------------------------------
# 5. Unrecognised robot names
# ---------------------------------------------------------

UNKNOWN_ROBOT_NAMES = [
    "Alexa",
    "Siri",
    "Computer",
    "Toaster",
]

for robot in UNKNOWN_ROBOT_NAMES:
    if robot.casefold() not in {
        name.casefold() for name in config.ROBOT_NAMES
    }:
        TEST_CASES.append(
            (f"Hi {robot}, I'm Simon", None)
        )


# ---------------------------------------------------------
# 6. Ordinary conversation and edge cases
# ---------------------------------------------------------

TEST_CASES.extend([
    ("Do you know Simon?", None),
    ("Simon likes astronomy", None),
    ("Alice is coming tomorrow", None),
    ("I'm Simon", None),
    ("My name is Alice", None),
    ("Hello, I'm Bob", None),
    ("", None),
    (" ", None),
    ("...", None),
    ("Simon", None),
])


# ---------------------------------------------------------
# 7. Run tests
# ---------------------------------------------------------

def run_tests():
    passed = 0
    failures = []

    for transcription, expected in TEST_CASES:
        actual = detector.detect(transcription)

        if actual == expected:
            passed += 1
        else:
            failures.append((transcription, expected, actual))

    print(f"\nTests run: {len(TEST_CASES)}")
    print(f"Passed:    {passed}")
    print(f"Failed:    {len(failures)}")

    for transcription, expected, actual in failures:
        print(f"\n[FAIL] {transcription!r}")
        print(f"  Expected: {expected!r}")
        print(f"  Actual:   {actual!r}")

    if failures:
        raise AssertionError(
            f"{len(failures)} UserDetector tests failed"
        )


if __name__ == "__main__":
    run_tests()
