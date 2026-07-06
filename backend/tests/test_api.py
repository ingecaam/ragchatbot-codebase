"""Tests for FastAPI endpoints: /api/query, /api/courses, /api/session/{id}."""
import pytest


# ─── POST /api/query ─────────────────────────────────────────────────────────

def test_query_auto_creates_session_when_none_given(api_client, mock_rag):
    resp = api_client.post("/api/query", json={"query": "What is MCP?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "test-session-abc"
    assert body["answer"] == "Test answer."
    assert isinstance(body["sources"], list)
    mock_rag.session_manager.create_session.assert_called_once()


def test_query_uses_caller_session_id_without_creating_new_one(api_client, mock_rag):
    resp = api_client.post(
        "/api/query", json={"query": "What is MCP?", "session_id": "caller-session"}
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "caller-session"
    mock_rag.session_manager.create_session.assert_not_called()


def test_query_returns_answer_and_sources_from_rag(api_client, mock_rag):
    mock_rag.query.return_value = (
        "The sky is blue.",
        [{"label": "Course A - Lesson 1", "url": "https://example.com/1"}],
    )
    resp = api_client.post("/api/query", json={"query": "What colour is the sky?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "The sky is blue."
    assert len(body["sources"]) == 1
    assert body["sources"][0]["label"] == "Course A - Lesson 1"


def test_query_forwards_user_query_to_rag(api_client, mock_rag):
    api_client.post("/api/query", json={"query": "Explain transformers."})
    call_query = mock_rag.query.call_args[0][0]
    assert "Explain transformers." in call_query


def test_query_missing_query_field_returns_422(api_client):
    resp = api_client.post("/api/query", json={})
    assert resp.status_code == 422


def test_query_rag_exception_returns_500(api_client, mock_rag):
    mock_rag.query.side_effect = RuntimeError("db connection lost")
    resp = api_client.post("/api/query", json={"query": "anything"})
    assert resp.status_code == 500
    assert "db connection lost" in resp.json()["detail"]


# ─── GET /api/courses ─────────────────────────────────────────────────────────

def test_courses_returns_analytics_from_rag(api_client, mock_rag):
    resp = api_client.get("/api/courses")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_courses"] == 2
    assert body["course_titles"] == ["Course A", "Course B"]


def test_courses_rag_exception_returns_500(api_client, mock_rag):
    mock_rag.get_course_analytics.side_effect = RuntimeError("analytics unavailable")
    resp = api_client.get("/api/courses")
    assert resp.status_code == 500
    assert "analytics unavailable" in resp.json()["detail"]


# ─── DELETE /api/session/{session_id} ─────────────────────────────────────────

def test_delete_existing_session_removes_it_and_returns_ok(api_client, mock_rag):
    mock_rag.session_manager.sessions["sess-to-delete"] = []
    resp = api_client.delete("/api/session/sess-to-delete")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert "sess-to-delete" not in mock_rag.session_manager.sessions


def test_delete_nonexistent_session_returns_ok_idempotently(api_client, mock_rag):
    resp = api_client.delete("/api/session/ghost-session")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
