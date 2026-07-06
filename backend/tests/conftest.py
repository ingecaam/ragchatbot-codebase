import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import chromadb
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from vector_store import SearchResults, VectorStore
from models import Course, Lesson, CourseChunk


def make_search_results(documents=None, metadata=None, distances=None, error=None):
    if error is not None:
        return SearchResults.empty(error)
    return SearchResults(
        documents=documents or [],
        metadata=metadata or [],
        distances=distances or [],
        error=None,
    )


@pytest.fixture(scope="session")
def seeded_store():
    """In-memory VectorStore with test data. Bypasses the on-disk chroma_db."""
    with patch("vector_store.chromadb.PersistentClient") as mock_persistent:
        mock_persistent.return_value = chromadb.EphemeralClient()
        store = VectorStore("./irrelevant", "all-MiniLM-L6-v2", 5)

        course = Course(
            title="MCP: Build Rich-Context AI Apps with Anthropic",
            course_link="https://www.deeplearning.ai/short-courses/mcp/",
            instructor="Elie Schoppik",
            lessons=[
                Lesson(
                    lesson_number=0,
                    title="Introduction",
                    lesson_link="https://learn.deeplearning.ai/mcp/0",
                ),
                Lesson(
                    lesson_number=1,
                    title="MCP Concepts",
                    lesson_link="https://learn.deeplearning.ai/mcp/1",
                ),
            ],
        )
        store.add_course_metadata(course)

        chunks = [
            CourseChunk(
                content="MCP stands for Model Context Protocol, a standard for "
                        "connecting AI models with external tools and data sources.",
                course_title="MCP: Build Rich-Context AI Apps with Anthropic",
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="MCP clients connect to MCP servers to access tools "
                        "and resources in a standardised way.",
                course_title="MCP: Build Rich-Context AI Apps with Anthropic",
                lesson_number=1,
                chunk_index=1,
            ),
        ]
        store.add_course_content(chunks)
        yield store


@pytest.fixture
def mock_rag():
    """Pre-configured MagicMock that stands in for RAGSystem in API tests."""
    m = MagicMock()
    m.session_manager.create_session.return_value = "test-session-abc"
    m.session_manager.sessions = {}
    m.query.return_value = ("Test answer.", [])
    m.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    m.add_course_folder.return_value = (0, 0)
    return m


@pytest.fixture
def api_client(mock_rag):
    """TestClient wired to the real FastAPI app with RAGSystem and StaticFiles mocked.

    Pops the cached `app` module so module-level initialisation (RAGSystem
    instantiation and StaticFiles mount) reruns under our patches each time.
    """
    sys.modules.pop("app", None)
    with (
        patch("rag_system.RAGSystem", return_value=mock_rag),
        patch("fastapi.staticfiles.StaticFiles"),
    ):
        import app as _app_module  # noqa: PLC0415
        yield TestClient(_app_module.app)
    sys.modules.pop("app", None)
