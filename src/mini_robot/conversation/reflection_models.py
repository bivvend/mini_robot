
from typing import Literal

from pydantic import BaseModel, Field


class MemoryProposal(BaseModel):
    type: Literal[
        "fact",
        "experience",
        "interest",
        "desire",
        "preference",
    ]

    subject: Literal["user", "robot", "world"]

    content: str = Field(
        description="A concise, standalone memory statement."
    )

    importance: int = Field(
        ge=1,
        le=5,
        description=(
            "Importance rating from 1 to 5. "
            "1 = trivial, 2 = minor, 3 = useful, "
            "4 = important, 5 = exceptionally important."
        ),
    )

    reason: str = Field(
        description="Why this information is worth remembering."
    )


class ReflectionResult(BaseModel):
    summary: str = Field(
        description="Brief summary of what was learned."
    )

    memories: list[MemoryProposal] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "Up to ten genuinely important new memories. "
            "Return an empty list if nothing significant was learned."
        ),
    )
