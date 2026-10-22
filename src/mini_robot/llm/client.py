import os
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(
        self,
        model: str = "local",
        base_url: str | None = "http://127.0.0.1:8080/v1",
        api_key: str | None = None,
        max_tokens: int = 2000,
        temperature: float | None = 0.8,
        reasoning_effort: str | None = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.is_remote = base_url is None

        if self.is_remote:
            self.client = OpenAI(
                api_key=api_key or os.environ["OPENAI_API_KEY"],
            )
        else:
            self.client = OpenAI(
                base_url=base_url,
                api_key=api_key or "not-needed",
            )

    def _get_params(self, messages):
        params = {
            "model": self.model,
            "messages": messages,
        }

        if self.is_remote:
            params["max_completion_tokens"] = self.max_tokens

            if self.reasoning_effort is not None:
                params["reasoning_effort"] = self.reasoning_effort

            if self.temperature is not None and not self.model.startswith("gpt-5"):
                params["temperature"] = self.temperature

        else:
            params["max_tokens"] = self.max_tokens

            if self.temperature is not None:
                params["temperature"] = self.temperature

        return params

    def generate(
        self,
        messages: list[dict[str, str]],
    ) -> str:

        response = self.client.chat.completions.create(
            **self._get_params(messages)
        )

        return response.choices[0].message.content or ""

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
    ) -> T:

        response = self.client.chat.completions.parse(
            **self._get_params(messages),
            response_format=response_model,
        )

        result = response.choices[0].message.parsed

        if result is None:
            raise ValueError("LLM returned no parsed response")

        return result
    def web_search(self, question: str) -> str:
        if not self.is_remote:
            raise RuntimeError("Web search requires remote OpenAI")

        response = self.client.responses.create(
            model=self.model,
            input=question,
            tools=[{"type": "web_search"}],
            tool_choice="required",
            max_output_tokens=self.max_tokens,
        )

        return response.output_text