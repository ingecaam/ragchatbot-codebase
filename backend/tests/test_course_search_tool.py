import pytest
from unittest.mock import MagicMock
from search_tools import CourseSearchTool
from vector_store import SearchResults

SUCCESS_DOCS = ["MCP stands for Model Context Protocol."]
SUCCESS_META = [{"course_title": "AI Fundamentals", "lesson_number": 1, "chunk_index": 0}]
SUCCESS_DISTS = [0.12]
SUCCESS_RESULTS = SearchResults(
    documents=SUCCESS_DOCS, metadata=SUCCESS_META, distances=SUCCESS_DISTS, error=None
)


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    store.get_course_link.return_value = "https://example.com/course"
    return store


@pytest.fixture
def tool(mock_store):
    return CourseSearchTool(mock_store)


def test_execute_successful_search_returns_formatted_string(tool, mock_store):
    mock_store.search.return_value = SUCCESS_RESULTS
    result = tool.execute("machine learning concepts")
    assert isinstance(result, str)
    assert "Course: AI Fundamentals" in result
    assert "Lesson 1" in result
    mock_store.search.assert_called_once_with(
        query="machine learning concepts", course_name=None, lesson_number=None
    )


def test_execute_empty_results_returns_no_content_message(tool, mock_store):
    empty = SearchResults(documents=[], metadata=[], distances=[], error=None)
    mock_store.search.return_value = empty
    result = tool.execute("obscure topic")
    assert result == "No relevant content found."


def test_execute_error_propagates_as_error_string(tool, mock_store):
    mock_store.search.return_value = SearchResults.empty("No course found matching 'XYZ'")
    result = tool.execute("anything", course_name="XYZ")
    assert result == "No course found matching 'XYZ'"
    mock_store.get_lesson_link.assert_not_called()


def test_course_name_passed_through_to_store_search(tool, mock_store):
    mock_store.search.return_value = SUCCESS_RESULTS
    tool.execute("some query", course_name="MCP")
    mock_store.search.assert_called_once_with(
        query="some query", course_name="MCP", lesson_number=None
    )


def test_lesson_number_passed_through_to_store_search(tool, mock_store):
    mock_store.search.return_value = SUCCESS_RESULTS
    tool.execute("intro content", lesson_number=2)
    mock_store.search.assert_called_once_with(
        query="intro content", course_name=None, lesson_number=2
    )


def test_last_sources_populated_after_successful_search(tool, mock_store):
    mock_store.search.return_value = SUCCESS_RESULTS
    mock_store.get_lesson_link.return_value = "https://example.com/lesson/1"
    tool.execute("machine learning concepts")
    assert len(tool.last_sources) == 1
    assert tool.last_sources[0]["label"] == "AI Fundamentals - Lesson 1"
    assert tool.last_sources[0]["url"] == "https://example.com/lesson/1"


def test_last_sources_unchanged_after_empty_search(tool, mock_store):
    empty = SearchResults(documents=[], metadata=[], distances=[], error=None)
    mock_store.search.return_value = empty
    tool.last_sources = []
    tool.execute("anything")
    assert tool.last_sources == []
