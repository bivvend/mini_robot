from openai import OpenAI
from pydantic import BaseModel

from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LLMClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        model: str = "local",
    ):
        self.model = model

        self.client = OpenAI(
            base_url=base_url,
            api_key="not-needed",
        )

    def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 200,
        temperature: float = 0.8,
    ) -> str:

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content or ""

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        max_tokens: int = 400,
        temperature: float = 0.8,
    ) -> T:

        response = self.client.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=response_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        result = response.choices[0].message.parsed

        if result is None:
            raise ValueError("LLM returned no parsed response")

        return result