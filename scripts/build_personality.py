from mini_robot.personality.personality import RobotPersonality

personality = RobotPersonality()

print(personality.name)
print(personality.traits.curiosity)

# Save the personality configuration
with open("data/personality.json", "w", encoding="utf-8") as f:
    f.write(personality.model_dump_json(indent=2))

