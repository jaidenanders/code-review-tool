"""TDD tests for POST /review/stream — Server-Sent Events endpoint."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db import get_db
from app.services.ollama_service import OllamaService
from app.services.review_service import ReviewService
from app.schemas.review import ReviewResult, CodeIssue, Severity, IssueCagetory

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.review import Base


# ── In-memory DB fixture ──────────────────────────────────────────────────────

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def good_review_result() -> ReviewResult:
    return ReviewResult(
        summary="Looks good overall.",
        score=82,
        issues=[
            CodeIssue(
                category=IssueCagetory.style,
                severity=Severity.warning,
                line=3,
                title="Naming convention",
                description="Use snake_case",
                suggestion="Rename variable",
            )
        ],
        strengths=["Readable logic"],
        raw_response="SUMMARY: ...\nSCORE: 82\n...",
    )


async def _token_generator(*tokens: str):
    for t in tokens:
        yield t


@pytest.fixture
def mock_ollama(good_review_result):
    """OllamaService with stream_review_code as an async generator and review_code returning raw text."""
    svc = MagicMock(spec=OllamaService)
    svc.stream_review_code = MagicMock(
        return_value=_token_generator("SUMMARY", ": looks good\n", "SCORE: 82\n", "END")
    )
    svc.review_code = AsyncMock(return_value=good_review_result.raw_response)
    return svc


@pytest.fixture
def mock_review_service(good_review_result):
    svc = MagicMock(spec=ReviewService)
    svc.review = AsyncMock(return_value=good_review_result)
    svc.parse_response = MagicMock(return_value=good_review_result)
    return svc


@pytest.fixture
def client(db_session, mock_ollama, mock_review_service):
    from app.api.routes.review import get_review_service, get_session_service, get_ollama
    from app.services.session_service import SessionService

    def override_db():
        yield db_session

    def override_ollama():
        return mock_ollama

    def override_review():
        return mock_review_service

    def override_session():
        return SessionService(db=db_session)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_ollama] = override_ollama
    app.dependency_overrides[get_review_service] = override_review
    app.dependency_overrides[get_session_service] = override_session

    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_sse(body: str) -> list[dict]:
    """Parse a raw SSE body into a list of {event, data} dicts."""
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type = None
        data_str = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_str = line[len("data:"):].strip()
        if event_type and data_str:
            events.append({"event": event_type, "data": json.loads(data_str)})
    return events


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestStreamingEndpoint:
    async def test_stream_returns_200(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/stream",
                json={"code": "x = 1", "filename": "a.py"},
            )
        assert resp.status_code == 200

    async def test_stream_content_type_is_event_stream(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/stream",
                json={"code": "x = 1", "filename": "a.py"},
            )
        assert "text/event-stream" in resp.headers["content-type"]

    async def test_stream_emits_token_events(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/stream",
                json={"code": "x = 1", "filename": "a.py"},
            )
        events = _parse_sse(resp.text)
        token_events = [e for e in events if e["event"] == "token"]
        assert len(token_events) > 0

    async def test_token_event_has_text_field(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/stream",
                json={"code": "x = 1", "filename": "a.py"},
            )
        events = _parse_sse(resp.text)
        token_events = [e for e in events if e["event"] == "token"]
        assert all("text" in e["data"] for e in token_events)

    async def test_stream_emits_result_event_last(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/stream",
                json={"code": "x = 1", "filename": "a.py"},
            )
        events = _parse_sse(resp.text)
        result_events = [e for e in events if e["event"] == "result"]
        assert len(result_events) == 1
        # result event should be last
        assert events[-1]["event"] == "result"

    async def test_result_event_has_session_id(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/stream",
                json={"code": "x = 1", "filename": "a.py"},
            )
        events = _parse_sse(resp.text)
        result = next(e["data"] for e in events if e["event"] == "result")
        assert "session_id" in result

    async def test_result_event_has_review_id(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/stream",
                json={"code": "x = 1", "filename": "a.py"},
            )
        events = _parse_sse(resp.text)
        result = next(e["data"] for e in events if e["event"] == "result")
        assert "review_id" in result

    async def test_result_event_has_score(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/stream",
                json={"code": "x = 1", "filename": "a.py"},
            )
        events = _parse_sse(resp.text)
        result = next(e["data"] for e in events if e["event"] == "result")
        assert "score" in result.get("result", {})

    async def test_existing_session_id_accepted(self, client):
        async with client as c:
            r1 = await c.post(
                "/api/v1/review/",
                json={"code": "x = 1", "filename": "init.py"},
            )
            session_id = r1.json()["session_id"]

            resp = await c.post(
                f"/api/v1/review/stream?session_id={session_id}",
                json={"code": "y = 2", "filename": "b.py"},
            )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        result = next(e["data"] for e in events if e["event"] == "result")
        assert result["session_id"] == session_id

    async def test_ollama_error_emits_error_event(self, client, mock_ollama):
        mock_ollama.stream_review_code = MagicMock(
            side_effect=RuntimeError("Ollama offline")
        )
        async with client as c:
            resp = await c.post(
                "/api/v1/review/stream",
                json={"code": "x = 1", "filename": "a.py"},
            )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1
        assert "message" in error_events[0]["data"]

    async def test_language_autodetected_from_filename(self, client, mock_ollama):
        mock_ollama.stream_review_code = MagicMock(
            return_value=_token_generator("SUMMARY: ok\nSCORE: 70\nEND")
        )
        async with client as c:
            await c.post(
                "/api/v1/review/stream",
                json={"code": "fn main() {}", "filename": "main.rs"},
            )
        call_kwargs = mock_ollama.stream_review_code.call_args
        used_lang = call_kwargs.kwargs.get("language") or (
            call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
        )
        assert used_lang == "rust"
