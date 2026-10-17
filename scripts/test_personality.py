from mini_robot.llm.client import LLMClient
from mini_robot.llm.models import RobotResponse
from mini_robot.personality.personality import RobotPersonality
from mini_robot.personality.engine import build_personality_prompt
import mini_robot.config as config

def main():
    from pathlib import Path

    # Locate the project root relative to this script
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    PERSONALITY_FILE = PROJECT_ROOT / "data" / config.PERSONALITY

    personality = RobotPersonality.model_validate_json(
        PERSONALITY_FILE.read_text(encoding="utf-8")
    )
    client = LLMClient()

    system_prompt = build_personality_prompt(personality)

    print("\n=== SYSTEM PROMPT ===\n")
    print(system_prompt)
    print("\n=== CONVERSATION ===\n")

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("quit", "exit"):
            break

        if not user_input:
            continue

        messages.append({
            "role": "user",
            "content": user_input,
        })

        try:
            response = client.generate_structured(
                messages=messages,
                response_model=RobotResponse,
                max_tokens=400,
            )
        except Exception as exc:
            messages.pop()
            print(f"LLM error: {exc}")
            continue

        print(f"\n{personality.name}: {response.speech}")
        print(
            f"     [emotion={response.emotion.value}, "
            f"gesture={response.gesture.value}]\n"
        )

        # Keep the structured response in conversation history.
        messages.append({
            "role": "assistant",
            "content": response.model_dump_json(),
        })


if __name__ == "__main__":
    main()