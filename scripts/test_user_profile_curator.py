
import logging

from mini_robot.conversation.memory import ConversationMemory
from mini_robot.conversation.user_profile import UserProfileStore
from mini_robot.conversation.user_profile_curator import UserProfileCurator
from mini_robot.llm.client import LLMClient
import mini_robot.config as config

logging.basicConfig(level=logging.INFO)

memory = ConversationMemory()
profile_store = UserProfileStore(memory.db_path)

llm = LLMClient(
    model="gpt-5.6-luna",
    base_url=None,
    max_tokens=2000,
    temperature=None,
    reasoning_effort="low",
)

curator = UserProfileCurator(
    llm=llm,
    conversation_memory=memory,
    profile_store=profile_store,
)

# Replace with an existing user ID from your database.
user_id = 1

profile = curator.curate(user_id)

print("\nUPDATED PROFILE:\n")
print(profile)

if curator.needs_update(user_id):
    profile = curator.curate(user_id)
    print(profile)
else:
    print("Profile is already up to date.")
