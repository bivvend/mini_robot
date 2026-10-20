
from mini_robot.conversation.semantic_memory import SemanticMemory


def main():
    memory = SemanticMemory()

    memory.add(
        type="fact",
        subject="user",
        content="The user is interested in astronomy.",
        importance=0.8,
    )

    memory.add(
        type="interest",
        subject="robot",
        content="Mini is fascinated by black holes.",
        importance=0.9,
    )

    memory.add(
        type="desire",
        subject="robot",
        content="Mini wants to understand how stars are born.",
        importance=0.85,
    )

    print("\nStored memories:\n")

    for item in memory.get():
        print(
            f"{item['id']:3} "
            f"[{item['subject']}/{item['type']}] "
            f"({item['importance']:.2f}) "
            f"{item['content']}"
        )


if __name__ == "__main__":
    main()
