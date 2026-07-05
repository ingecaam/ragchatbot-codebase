import pytest
from unittest.mock import MagicMock, patch
import anthropic as anthropic_module
from ai_generator import AIGenerator

TOOL_DEFS = [{
    "name": "course_lookup",
    "description": "search",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}]


def make_text_block(text="Here is the answer."):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(tool_id="toolu_abc", name="course_lookup", input_dict=None):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_dict or {"query": "machine learning"}
    return block


def make_message(stop_reason, content_blocks):
    msg = MagicMock()
    msg.stop_reason = stop_reason
    msg.content = content_blocks
    return msg


@pytest.fixture
def mock_client():
    with patch("anthropic.Anthropic") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client


@pytest.fixture
def generator(mock_client):
    return AIGenerator(api_key="fake-api-key", model="claude-sonnet-4-6")


@pytest.fixture
def mock_tool_manager():
    tm = MagicMock()
    tm.execute_tool.return_value = "Relevant course content here."
    return tm


def test_end_turn_returns_text_directly(generator, mock_client):
    mock_client.messages.create.return_value = make_message(
        "end_turn", [make_text_block("Direct answer.")]
    )
    result = generator.generate_response("What is 2+2?")
    assert result == "Direct answer."
    assert mock_client.messages.create.call_count == 1


def test_tool_use_triggers_second_api_call(generator, mock_client, mock_tool_manager):
    first_resp = make_message("tool_use", [make_tool_use_block()])
    second_resp = make_message("end_turn", [make_text_block("Final answer.")])
    mock_client.messages.create.side_effect = [first_resp, second_resp]
    result = generator.generate_response(
        "What is ML?", tools=TOOL_DEFS, tool_manager=mock_tool_manager
    )
    assert mock_client.messages.create.call_count == 2
    assert result == "Final answer."


def test_tools_included_in_first_api_call(generator, mock_client):
    mock_client.messages.create.return_value = make_message(
        "end_turn", [make_text_block("Answer.")]
    )
    generator.generate_response("test query", tools=TOOL_DEFS)
    first_call_kwargs = mock_client.messages.create.call_args_list[0].kwargs
    assert "tools" in first_call_kwargs
    assert first_call_kwargs["tools"] == TOOL_DEFS


def test_tool_choice_auto_set_when_tools_provided(generator, mock_client):
    mock_client.messages.create.return_value = make_message(
        "end_turn", [make_text_block("Answer.")]
    )
    generator.generate_response("query", tools=TOOL_DEFS)
    first_call_kwargs = mock_client.messages.create.call_args_list[0].kwargs
    assert first_call_kwargs.get("tool_choice") == {"type": "auto"}


def test_no_tools_in_params_when_tools_not_provided(generator, mock_client):
    mock_client.messages.create.return_value = make_message(
        "end_turn", [make_text_block("Answer.")]
    )
    generator.generate_response("What is Python?")
    first_call_kwargs = mock_client.messages.create.call_args_list[0].kwargs
    assert "tools" not in first_call_kwargs
    assert "tool_choice" not in first_call_kwargs


def test_execute_tool_called_with_correct_name_and_kwargs(generator, mock_client, mock_tool_manager):
    tool_block = make_tool_use_block(
        tool_id="toolu_xyz",
        name="course_lookup",
        input_dict={"query": "what is MCP", "course_name": "MCP"},
    )
    first_resp = make_message("tool_use", [tool_block])
    second_resp = make_message("end_turn", [make_text_block("MCP answer.")])
    mock_client.messages.create.side_effect = [first_resp, second_resp]
    generator.generate_response("what is MCP", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    mock_tool_manager.execute_tool.assert_called_once_with(
        "course_lookup", query="what is MCP", course_name="MCP"
    )


def test_final_call_after_two_rounds_has_no_tools(generator, mock_client, mock_tool_manager):
    first_resp = make_message("tool_use", [make_tool_use_block()])
    second_resp = make_message("tool_use", [make_tool_use_block(tool_id="toolu_def")])
    third_resp = make_message("end_turn", [make_text_block("Done.")])
    mock_client.messages.create.side_effect = [first_resp, second_resp, third_resp]
    generator.generate_response("query", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    third_call_kwargs = mock_client.messages.create.call_args_list[2].kwargs
    assert "tools" not in third_call_kwargs
    assert "tool_choice" not in third_call_kwargs


def test_two_sequential_tool_rounds_makes_three_api_calls(generator, mock_client, mock_tool_manager):
    first_resp = make_message("tool_use", [make_tool_use_block()])
    second_resp = make_message("tool_use", [make_tool_use_block(tool_id="toolu_def")])
    third_resp = make_message("end_turn", [make_text_block("Final answer.")])
    mock_client.messages.create.side_effect = [first_resp, second_resp, third_resp]
    result = generator.generate_response("query", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    assert mock_client.messages.create.call_count == 3
    assert result == "Final answer."


def test_intermediate_call_includes_tools(generator, mock_client, mock_tool_manager):
    first_resp = make_message("tool_use", [make_tool_use_block()])
    second_resp = make_message("tool_use", [make_tool_use_block(tool_id="toolu_def")])
    third_resp = make_message("end_turn", [make_text_block("Done.")])
    mock_client.messages.create.side_effect = [first_resp, second_resp, third_resp]
    generator.generate_response("query", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    second_call_kwargs = mock_client.messages.create.call_args_list[1].kwargs
    assert second_call_kwargs.get("tools") == TOOL_DEFS
    assert second_call_kwargs.get("tool_choice") == {"type": "auto"}


def test_early_exit_when_intermediate_returns_end_turn(generator, mock_client, mock_tool_manager):
    first_resp = make_message("tool_use", [make_tool_use_block()])
    second_resp = make_message("end_turn", [make_text_block("Early answer.")])
    mock_client.messages.create.side_effect = [first_resp, second_resp]
    result = generator.generate_response("query", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    assert mock_client.messages.create.call_count == 2
    assert result == "Early answer."


def test_message_accumulation_two_rounds(generator, mock_client, mock_tool_manager):
    first_resp = make_message("tool_use", [make_tool_use_block(tool_id="toolu_1")])
    second_resp = make_message("tool_use", [make_tool_use_block(tool_id="toolu_2")])
    third_resp = make_message("end_turn", [make_text_block("Done.")])
    mock_client.messages.create.side_effect = [first_resp, second_resp, third_resp]
    generator.generate_response("user question", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    final_messages = mock_client.messages.create.call_args_list[2].kwargs["messages"]
    # [user, assistant(tool_use round1), user(tool_result round1),
    #  assistant(tool_use round2), user(tool_result round2)]
    assert len(final_messages) == 5
    assert final_messages[0]["role"] == "user"
    assert final_messages[1]["role"] == "assistant"
    assert final_messages[2]["role"] == "user"
    assert any(b.get("type") == "tool_result" for b in final_messages[2]["content"])
    assert final_messages[3]["role"] == "assistant"
    assert final_messages[4]["role"] == "user"
    assert any(b.get("type") == "tool_result" for b in final_messages[4]["content"])


def test_execute_tool_called_once_per_round_in_two_rounds(generator, mock_client, mock_tool_manager):
    first_resp = make_message("tool_use", [make_tool_use_block(tool_id="toolu_1")])
    second_resp = make_message("tool_use", [make_tool_use_block(tool_id="toolu_2")])
    third_resp = make_message("end_turn", [make_text_block("Done.")])
    mock_client.messages.create.side_effect = [first_resp, second_resp, third_resp]
    generator.generate_response("query", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    assert mock_tool_manager.execute_tool.call_count == 2


def test_tool_execution_failure_falls_through_to_final_call(generator, mock_client, mock_tool_manager):
    mock_tool_manager.execute_tool.side_effect = RuntimeError("db error")
    first_resp = make_message("tool_use", [make_tool_use_block()])
    final_resp = make_message("end_turn", [make_text_block("Degraded answer.")])
    mock_client.messages.create.side_effect = [first_resp, final_resp]
    result = generator.generate_response("query", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    assert mock_client.messages.create.call_count == 2
    final_call_kwargs = mock_client.messages.create.call_args_list[1].kwargs
    assert "tools" not in final_call_kwargs
    assert result == "Degraded answer."


def test_tool_execution_failure_includes_error_in_tool_result(generator, mock_client, mock_tool_manager):
    mock_tool_manager.execute_tool.side_effect = RuntimeError("db error")
    first_resp = make_message("tool_use", [make_tool_use_block(tool_id="toolu_err")])
    final_resp = make_message("end_turn", [make_text_block("Answer.")])
    mock_client.messages.create.side_effect = [first_resp, final_resp]
    generator.generate_response("query", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    final_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result_message = final_messages[2]  # [user, assistant, user(tool_result)]
    tool_result_content = tool_result_message["content"][0]["content"]
    assert "db error" in tool_result_content


def test_max_rounds_hard_cap_at_two(generator, mock_client, mock_tool_manager):
    resp_tool = lambda tid: make_message("tool_use", [make_tool_use_block(tool_id=tid)])
    mock_client.messages.create.side_effect = [
        resp_tool("t1"), resp_tool("t2"), resp_tool("t3"),
        make_message("end_turn", [make_text_block("Done.")])
    ]
    generator.generate_response("query", tools=TOOL_DEFS, tool_manager=mock_tool_manager)
    assert mock_client.messages.create.call_count == 3


def test_value_error_raised_when_final_response_empty(generator, mock_client, mock_tool_manager):
    first_resp = make_message("tool_use", [make_tool_use_block()])
    empty_resp = MagicMock()
    empty_resp.stop_reason = "end_turn"
    empty_resp.content = []
    mock_client.messages.create.side_effect = [first_resp, empty_resp]
    with pytest.raises(ValueError, match="Empty response from API"):
        generator.generate_response("query", tools=TOOL_DEFS, tool_manager=mock_tool_manager)


def test_api_connection_error_is_reraised(generator, mock_client):
    mock_client.messages.create.side_effect = anthropic_module.APIConnectionError(
        request=MagicMock()
    )
    with pytest.raises(anthropic_module.APIConnectionError):
        generator.generate_response("query")


def test_api_status_error_is_reraised(generator, mock_client):
    status_error = anthropic_module.APIStatusError(
        message="model_not_found",
        response=MagicMock(status_code=404),
        body={"error": {"type": "not_found_error"}},
    )
    mock_client.messages.create.side_effect = status_error
    with pytest.raises(anthropic_module.APIStatusError):
        generator.generate_response("query")
