from mini_robot.config import (
    LLAMA_SERVER,
    LLAMA_MODEL,
    LLAMA_HOST,
    LLAMA_PORT,
)

from mini_robot.llm.server import LLMServer
from mini_robot.llm.client import LLMClient
from mini_robot.llm.models import RobotResponse


server = LLMServer(
    executable=LLAMA_SERVER,
    model_path=LLAMA_MODEL,
    host=LLAMA_HOST,
    port=LLAMA_PORT,
)

server.start()

client = LLMClient(
    base_url=f"{server.base_url}/v1",
)

messages = [
    {
        "role": "system",
        "content": "You are a curious, mischievous little robot.",
    },
    {
        "role": "user",
        "content": "Hello! What are you thinking about?",
    },
]

response = client.generate_structured(
    messages=messages,
    response_model=RobotResponse,
)

print(response.model_dump_json(indent=2))