import os
import pytest
from unittest.mock import MagicMock, patch

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(BACKEND_DIR, "chroma_db")
CHROMA_EXISTS = os.path.exists(CHROMA_PATH)

from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, ToolManager
from ai_generator import AIGenerator


# ─── CANARY TESTS: real chroma_db on disk ────────────────────────────────────

def test_chroma_db_can_be_opened():
    """
    PRIMARY CANARY: fails with pyo3 PanicException if chroma_db/ is in the
    old pre-1.0 HNSW format incompatible with chromadb==1.0.15.
    FIX: delete backend/chroma_db/ then restart the app to re-ingest docs/.
    """
    if not CHROMA_EXISTS:
        pytest.skip("chroma_db does not exist — run the app once to ingest")
    try:
        VectorStore(CHROMA_PATH, "all-MiniLM-L6-v2", 5)
    except Exception as e:
        pytest.fail(
            f"chroma_db failed to open: {type(e).__name__}: {e}\n"
            "Root cause: likely old ChromaDB format incompatible with chromadb==1.0.15.\n"
            "Fix: delete backend/chroma_db/ and restart the app to re-ingest."
        )


@pytest.mark.skipif(not CHROMA_EXISTS, reason="chroma_db missing")
def test_course_content_collection_has_documents():
    """Confirms data was ingested. Empty DB means ingestion never ran or failed."""
    try:
        store = VectorStore(CHROMA_PATH, "all-MiniLM-L6-v2", 5)
    except Exception:
        pytest.skip("chroma_db could not be opened — covered by test_chroma_db_can_be_opened")
    count = store.course_content.count()
    assert count > 0, (
        f"course_content collection is empty (count={count}). "
        "Re-ingest: restart the app or call rag_system.add_course_folder('../docs')."
    )


@pytest.mark.skipif(not CHROMA_EXISTS, reason="chroma_db missing")
def test_course_catalog_has_entries():
    """Confirms course metadata was ingested."""
    try:
        store = VectorStore(CHROMA_PATH, "all-MiniLM-L6-v2", 5)
    except Exception:
        pytest.skip("chroma_db could not be opened")
    count = store.course_catalog.count()
    assert count > 0, f"course_catalog is empty (count={count}). Re-ingest docs/."


@pytest.mark.skipif(not CHROMA_EXISTS, reason="chroma_db missing")
def test_resolve_course_name_returns_match():
    """
    Tests failure mode: _resolve_course_name returning None silently.
    If this fails with a populated DB, every course-filtered search returns
    SearchResults.empty() → tool returns an error string → Claude says "not found".
    """
    try:
        store = VectorStore(CHROMA_PATH, "all-MiniLM-L6-v2", 5)
    except Exception:
        pytest.skip("chroma_db could not be opened")
    result = store._resolve_course_name("MCP")
    assert result is not None, (
        "_resolve_course_name('MCP') returned None. "
        "Either course_catalog is empty or the vector lookup failed silently."
    )
    assert "MCP" in result, f"Resolved title '{result}' does not contain 'MCP'"


@pytest.mark.skipif(not CHROMA_EXISTS, reason="chroma_db missing")
def test_real_search_returns_results():
    """End-to-end: VectorStore.search() returns non-empty results for a known topic."""
    try:
        store = VectorStore(CHROMA_PATH, "all-MiniLM-L6-v2", 5)
    except Exception:
        pytest.skip("chroma_db could not be opened")
    results = store.search("what is MCP")
    assert not results.is_empty(), (
        f"search('what is MCP') returned empty results. error={results.error!r}. "
        "course_content collection may be empty or not ingested."
    )
    assert results.error is None, f"search returned an error: {results.error}"


# ─── LOGIC TESTS: seeded in-memory VectorStore ───────────────────────────────

def test_seeded_store_resolve_course_name(seeded_store):
    """Verifies _resolve_course_name works on a known-good in-memory DB."""
    result = seeded_store._resolve_course_name("MCP")
    assert result == "MCP: Build Rich-Context AI Apps with Anthropic"


def test_seeded_store_search_returns_results(seeded_store):
    results = seeded_store.search("what is MCP")
    assert not results.is_empty()
    assert results.error is None
    assert len(results.documents) > 0


def test_course_search_tool_execute_returns_content(seeded_store):
    """Integration: real VectorStore + real CourseSearchTool."""
    tool = CourseSearchTool(seeded_store)
    result = tool.execute("MCP protocol")
    assert isinstance(result, str)
    assert len(result) > 0
    assert result != "No relevant content found."
    assert "Course:" in result


def test_full_tool_use_pipeline_with_real_vector_store(seeded_store):
    """
    Integration: mocked Anthropic client + real VectorStore + real tools.
    Verifies the complete AIGenerator → ToolManager → CourseSearchTool → VectorStore chain.
    The tool must produce real, non-error content that gets sent in the second API call.
    """
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "toolu_integration_001"
    tool_block.name = "course_lookup"
    tool_block.input = {"query": "what is MCP"}

    first_response = MagicMock()
    first_response.stop_reason = "tool_use"
    first_response.content = [tool_block]

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "MCP stands for Model Context Protocol."

    second_response = MagicMock()
    second_response.stop_reason = "end_turn"
    second_response.content = [text_block]

    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [first_response, second_response]

        generator = AIGenerator(api_key="fake-key", model="claude-sonnet-4-6")
        search_tool = CourseSearchTool(seeded_store)
        tool_manager = ToolManager()
        tool_manager.register_tool(search_tool)

        result = generator.generate_response(
            query="what is MCP?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

    assert result == "MCP stands for Model Context Protocol."
    assert mock_client.messages.create.call_count == 2

    # Verify the tool produced real content (not an error string)
    second_call_msgs = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result_msg = second_call_msgs[-1]
    assert tool_result_msg["role"] == "user"
    tool_result_content = tool_result_msg["content"][0]["content"]
    assert isinstance(tool_result_content, str)
    assert len(tool_result_content) > 0
    assert "No course found matching" not in tool_result_content
    assert "Search error" not in tool_result_content
