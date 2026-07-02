# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack RAG chatbot that answers questions about educational course transcripts. Users ask natural-language questions; the backend uses Anthropic tool-use to let Claude autonomously decide when to search a ChromaDB vector store before generating an answer.

**Stack:** Python 3.13 + FastAPI backend, vanilla JS/HTML/CSS frontend, ChromaDB for vector storage, `sentence-transformers` for embeddings, Anthropic Claude as the LLM.

## Commands

**Package manager:** `uv` (not pip directly)

```bash
# Install dependencies
uv sync

# Run the app (from project root)
./run.sh

# Or manually (from project root)
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app serves at `http://localhost:8000`. Swagger UI at `http://localhost:8000/docs`. There is no test suite.

**Required:** Create a `.env` file at the project root (copy from `.env.example`) with `ANTHROPIC_API_KEY`.

## Architecture

### Agentic tool-use RAG (not classic retrieve-then-generate)

The core design in `backend/ai_generator.py` exposes ChromaDB search as an Anthropic tool (`search_course_content`). Claude decides whether and how to call the tool — the system prompt instructs it to make at most one search per query. This is a single-round tool-use loop, not a chained pipeline.

```
User query → SessionManager (history) → AIGenerator
  → Claude API (with tool definition)
  → [optional] tool_use block → CourseSearchTool → VectorStore
  → final Claude response
```

### Two ChromaDB collections

`backend/vector_store.py` maintains:
- `course_catalog` — course-level metadata for semantic course-name resolution
- `course_content` — sentence-chunked transcript text, filterable by `course_title` and `lesson_number`

When a search specifies a course name, `_resolve_course_name()` does a vector similarity lookup against `course_catalog` first, then applies the resolved title as a `where` filter on `course_content`.

### Document ingestion

On FastAPI `startup`, `backend/app.py` scans `../docs/` and ingests any `.txt`/`.pdf`/`.docx` not already in the store. Ingestion is synchronous (not backgrounded). The course title is the deduplication key — re-running won't re-ingest already-indexed courses.

Course transcript files must follow the parser format in `backend/document_processor.py`:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <title>
Lesson Link: <url>
<transcript text>
```

### Frontend served by FastAPI

`backend/app.py` mounts `../frontend` as a `StaticFiles` endpoint at `/`. No separate web server. The `DevStaticFiles` subclass (adds `no-cache` headers) is defined but not currently used in the mount.

### Session management

`backend/session_manager.py` stores conversation history in an in-memory dict. History is capped at `MAX_HISTORY=2` exchanges and passed to Claude as plain text in the system prompt (not as structured `messages`). No persistence — sessions reset on server restart.

### Configuration

All tunable constants live in `backend/config.py` (model name, chunk size/overlap, ChromaDB path, API key). Change behavior there rather than in individual modules.
