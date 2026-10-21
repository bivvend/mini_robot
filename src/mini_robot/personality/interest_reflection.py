
from pydantic import BaseModel, Field


class InterestUpdate(BaseModel):
    topic: str
    enthusiasm_change: float = Field(ge=-0.1, le=0.1)
    curiosity_change: float = Field(ge=-0.1, le=0.1)
    reason: str


class NewInterest(BaseModel):
    topic: str
    enthusiasm: float = Field(default=0.4, ge=0, le=1)
    curiosity: float = Field(default=0.6, ge=0, le=1)
    description: str = ""


class InterestReflectionResult(BaseModel):
    summary: str = ""
    updates: list[InterestUpdate] = Field(default_factory=list)
    new_interests: list[NewInterest] = Field(default_factory=list)
