from enum import Enum

from pydantic import BaseModel, Field


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    CURIOUS = "curious"
    EXCITED = "excited"
    CONFUSED = "confused"
    SAD = "sad"
    MISCHIEVOUS = "mischievous"


class Gesture(str, Enum):
    NONE = "none"
    NOD = "nod"
    SHAKE_HEAD = "shake_head"
    TILT_HEAD = "tilt_head"
    LOOK_AROUND = "look_around"


class RobotResponse(BaseModel):
    speech: str = Field(
        description="The words the robot should speak aloud."
    )

    emotion: Emotion = Field(
        description="The emotion the robot should express."
    )

    gesture: Gesture = Field(
        description="A simple physical gesture accompanying the speech."
    )