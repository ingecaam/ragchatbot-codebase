import json

import anthropic
from typing import List, Optional, Dict, Any
from config import config

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Up to two searches per query** — use a second search only when the first result is insufficient to answer the question
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives
- **Course outline queries** (e.g. "what lessons does X have", "outline of X", "list lessons in X"): Use the course_outline tool; respond with the course title, course link, and each lesson number with its title

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        try:
            response = self.client.messages.create(**api_params)
        except anthropic.APIConnectionError as e:
            print(f"Connection error: {e}")
            raise
        except anthropic.RateLimitError as e:
            print(f"Rate limit error: {e}")
            raise
        except anthropic.APIStatusError as e:
            print(f"API error - Status: {e.status_code}, Message: {e.message}")
            print(f"Full response: {e.response}")
            raise
        except Exception as e:
            print(f"Unexpected error: {type(e).__name__}: {e}")
            raise
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager, tools)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager, tools=None):
        """
        Handle sequential tool-call rounds (up to config.MAX_TOOL_ROUNDS) and return
        the final synthesized response.

        Tools remain available on intermediate API calls so Claude can chain searches.
        They are stripped only from the final call.
        """
        messages = base_params["messages"].copy()
        system = base_params["system"]
        current_resp = initial_response  # stop_reason == "tool_use" on entry

        for round_num in range(config.MAX_TOOL_ROUNDS):
            # Serialize assistant content to plain dicts (avoid Pydantic objects)
            assistant_content = []
            for block in current_resp.content:
                if block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
                elif block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute tool calls; catch errors per-block for graceful degradation
            tool_results = []
            tool_failed = False
            for block in current_resp.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = f"Tool execution failed: {e}"
                        tool_failed = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})

            # Stop looping if this was the last round or a tool failed
            is_last_round = (round_num == config.MAX_TOOL_ROUNDS - 1) or tool_failed
            if is_last_round:
                break

            # Intermediate call WITH tools so Claude can request another search
            intermediate_resp = self.client.messages.create(
                **self.base_params,
                messages=messages,
                system=system,
                tools=tools,
                tool_choice={"type": "auto"}
            )

            if intermediate_resp.stop_reason != "tool_use":
                # Claude has a text answer — return it directly, no extra call needed
                if not intermediate_resp.content:
                    raise ValueError(
                        f"Empty response from API. Stop reason: {intermediate_resp.stop_reason}"
                    )
                return intermediate_resp.content[0].text

            current_resp = intermediate_resp

        # Final call WITHOUT tools — Claude synthesizes from accumulated results
        final_response = self.client.messages.create(
            **self.base_params,
            messages=messages,
            system=system
        )

        if not final_response.content:
            raise ValueError(f"Empty response from API. Stop reason: {final_response.stop_reason}")

        return final_response.content[0].text