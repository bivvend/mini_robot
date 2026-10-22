from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5.6-luna",
    tools=[
        {"type": "web_search"}
    ],
    tool_choice="required",
    input="What are the latest developments in space exploration this week?",
)

print(response.output_text)