import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    temperature=0,
    max_tokens=800,
    system="You are a helpful assistant.",
    messages=[
        {
            "role": "user",
            "content": "What is the outline of the MCP course?"
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_test123",
                    "name": "search_course_content",
                    "input": {"query": "course outline"}
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_test123",
                    "content": "Lesson 0: Introduction. Lesson 5: Primitives. Lesson 10: Conclusion."
                }
            ]
        }
    ]
)

print(f"Stop reason: {response.stop_reason}")
print(f"Content: {response.content}")