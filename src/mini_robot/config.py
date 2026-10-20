# src/mini_robot/config.py

from pathlib import Path

LLAMA_SERVER = Path(
    r"D:\repos2\llama.cpp\build-vulkan\bin\llama-server.exe"
)

LLAMA_MODEL = Path(
    r"D:\repos2\llama.cpp\models\Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
)

LLAMA_HOST = "127.0.0.1"
LLAMA_PORT = 8080

PERSONALITY = "personality_super_cute.json"