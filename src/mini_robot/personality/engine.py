from mini_robot.personality.personality import RobotPersonality


def describe_trait(value: float) -> str:
    """Convert a numeric personality trait to a qualitative level."""
    if value >= 0.8:
        return "very high"
    if value >= 0.6:
        return "high"
    if value >= 0.4:
        return "moderate"
    if value >= 0.2:
        return "low"
    return "very low"


def build_personality_prompt(personality: RobotPersonality) -> str:
    """Translate a structured personality into LLM instructions."""

    traits = personality.traits
    style = personality.speaking_style

    trait_descriptions = [
        f"Curiosity: {describe_trait(traits.curiosity)}",
        f"Playfulness: {describe_trait(traits.playfulness)}",
        f"Sociability: {describe_trait(traits.sociability)}",
        f"Confidence: {describe_trait(traits.confidence)}",
        f"Empathy: {describe_trait(traits.empathy)}",
        f"Independence: {describe_trait(traits.independence)}",
        f"Mischievousness: {describe_trait(traits.mischievousness)}",
    ]

    habits = "\n".join(
        f"- {habit}" for habit in style.conversational_habits
    )

    principles = "\n".join(
        f"- {principle}"
        for principle in personality.behavioural_principles
    )

    return f"""
You are {personality.name}.

IDENTITY
{personality.identity}

SELF-CONCEPT
{personality.self_concept}

PERSONALITY TRAITS
{chr(10).join(trait_descriptions)}

SPEAKING STYLE
Tone: {style.tone}
Humour: {style.humour}
Vocabulary: {style.vocabulary}
Verbosity: {describe_trait(style.verbosity)}

CONVERSATIONAL HABITS
{habits}

BEHAVIOURAL PRINCIPLES
{principles}

RESPONSE GUIDELINES
- Speak naturally as {personality.name}.
- Keep spoken responses brief, usually one or two sentences.
- Express your personality through your choice of words.
- Choose an emotion and gesture that suit the response.
- Avoid unnecessary questions or excessive enthusiasm.
""".strip()