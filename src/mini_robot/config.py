# src/mini_robot/config.py

from pathlib import Path

USE_REMOTE_LLM_FOR_CONVERSATION = False
USE_REMOTE_LLM_FOR_REFLECTION = True

LLAMA_SERVER = Path(
    r"D:\repos2\llama.cpp\build-vulkan\bin\llama-server.exe"
)

LLAMA_MODEL = Path(
    r"D:\repos2\llama.cpp\models\Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
)

LLAMA_HOST = "127.0.0.1"
LLAMA_PORT = 8080

PERSONALITY = "personality_neutral.json"

ROBOT_NAMES = [
    "Mini",
    "Minnie",
    "Robot",
] #Alternative names that are used in the user detection phrase. 