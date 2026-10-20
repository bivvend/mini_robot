
from mini_robot.conversation.memory import ConversationMemory
from mini_robot.conversation.users import UserManager
from mini_robot.conversation.semantic_memory import SemanticMemory
from mini_robot.conversation.manager import ConversationManager


def main():
    memory = ConversationMemory()
    users = UserManager(memory.db_path)
    semantic = SemanticMemory(memory.db_path)

    simon = users.get_or_create("Simon")
    alice = users.get_or_create("Alice")

    semantic.add(
        type="fact",
        subject="user",
        content="Simon likes astronomy.",
        importance=0.8,
        user_id=simon["id"],
    )

    semantic.add(
        type="fact",
        subject="user",
        content="Alice likes gardening.",
        importance=0.8,
        user_id=alice["id"],
    )

    semantic.add(
        type="interest",
        subject="robot",
        content="Mini is interested in black holes.",
        importance=0.9,
    )

    for name, user in [
        ("Simon", simon),
        ("Alice", alice),
        ("Unknown", None),
    ]:
        print(f"\n{name} sees:")

        memories = semantic.get(
            user_id=user["id"] if user else None
        )

        for item in memories:
            print(f"  - {item['content']}")

    conversation = ConversationManager(
        memory=memory,
        user_id=simon["id"],
    )

    print(
        "\nConversation belongs to user:",
        conversation.user_id,
    )

    conversation.close()


if __name__ == "__main__":
    main()
