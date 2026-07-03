import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    temperature=0,
    max_tokens=4096,
    messages=[
    {
      "role": "user",
      "content": "What is the outline of the MCP Build Rich-Context AI Apps with Anthropic course?"
    },
    {
      "role": "assistant",
      "content": [
        {
          "type": "tool_use",
          "id": "toolu_test125",
          "name": "course_lookup",
          "input": {
            "query": "course outline",
            "course_name": "MCP Build Rich-Context AI Apps with Anthropic"
          }
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_test125",
          "content": "Course: MCP Build Rich-Context AI Apps with Anthropic. Found content in Lesson 0, Lesson 5, Lesson 10."
        }
      ]
    }
  ]
)
# response = client.messages.create(
#     model="claude-sonnet-4-6",
#     max_tokens=100,
#     messages=[
#         {"role": "user", "content": "What is 2+2?"},
#         {"role": "assistant", "content": [
#             {"type": "tool_use", "id": "abc123", "name": "calculator", "input": {"x": 2, "y": 2}}
#         ]},
#         {"role": "user", "content": [
#             {"type": "tool_result", "tool_use_id": "abc123", "content": "4"}
#         ]}
#     ]
# )
print(f"Stop reason: {response.stop_reason}")
print(f"Content: {response.content}")