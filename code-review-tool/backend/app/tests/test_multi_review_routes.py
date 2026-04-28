"""TDD tests for POST /review/multi endpoint."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db import get_db
from app.services.ollama_service import OllamaService
from app.services.review_service import ReviewService
from app.schemas.review import ReviewResult, CodeIssue, Severity, IssueCagetory

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.review import Base


# ── In-memory DB fixture (reused from other route tests) ──────────────────────

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
        score=80,
        issues=[
            CodeIssue(
                category=IssueCagetory.style,
                severity=Severity.warning,
                line=5,
                title="Inconsistent naming",
                description="Use camelCase",
                suggestion="Rename variable",
            )
        ],
        strengths=["Good separation of concerns"],
        raw_response="SUMMARY: ...\nSCORE: 80\n...",
    )


@pytest.fixture
def mock_review_service(good_review_result):
    svc = MagicMock(spec=ReviewService)
    svc.review = AsyncMock(return_value=good_review_result)
    return svc


@pytest.fixture
def client(db_session, mock_review_service):
    from app.api.routes.review import get_review_service, get_session_service
    from app.services.session_service import SessionService

    def override_db():
        yield db_session

    def override_review():
        return mock_review_service

    def override_session():
        return SessionService(db=db_session)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_review_service] = override_review
    app.dependency_overrides[get_session_service] = override_session

    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    app.dependency_overrides.clear()


class TestMultiFileReview:
    async def test_post_multi_returns_200(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={"files": [{"filename": "app.py", "code": "x = 1"}]},
            )
        assert resp.status_code == 200

    async def test_response_has_session_id(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={"files": [{"filename": "a.py", "code": "x=1"}]},
            )
        assert "session_id" in resp.json()

    async def test_response_has_review_id(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={"files": [{"filename": "a.py", "code": "x=1"}]},
            )
        assert "review_id" in resp.json()

    async def test_response_has_aggregated_result(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={"files": [{"filename": "a.py", "code": "x=1"}]},
            )
        body = resp.json()
        assert "result" in body
        assert "score" in body["result"]

    async def test_response_has_per_file_breakdown(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={
                    "files": [
                        {"filename": "a.py", "code": "x=1"},
                        {"filename": "b.ts", "code": "const y = 2"},
                    ]
                },
            )
        body = resp.json()
        assert "per_file" in body
        assert len(body["per_file"]) == 2

    async def test_per_file_has_filename_and_language(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={"files": [{"filename": "main.go", "code": "package main"}]},
            )
        per_file = resp.json()["per_file"][0]
        assert per_file["filename"] == "main.go"
        assert per_file["language"] == "go"

    async def test_language_auto_detected_from_extension(self, client, mock_review_service):
        async with client as c:
            await c.post(
                "/api/v1/review/multi",
                json={"files": [{"filename": "server.ts", "code": "const x = 1"}]},
            )
        call_kwargs = mock_review_service.review.call_args
        assert call_kwargs.kwargs.get("language") == "typescript" or (
            call_kwargs.args and call_kwargs.args[1] == "typescript"
        )

    async def test_total_chunks_reported(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={"files": [{"filename": "a.py", "code": "x=1"}]},
            )
        assert "total_chunks" in resp.json()
        assert resp.json()["total_chunks"] >= 1

    async def test_existing_session_id_accepted(self, client):
        # Create a session first via single review
        async with client as c:
            r1 = await c.post(
                "/api/v1/review/",
                json={"code": "x = 1", "filename": "init.py"},
            )
            session_id = r1.json()["session_id"]

            resp = await c.post(
                f"/api/v1/review/multi?session_id={session_id}",
                json={"files": [{"filename": "a.py", "code": "y = 2"}]},
            )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id

    async def test_empty_files_returns_422(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={"files": []},
            )
        assert resp.status_code == 422

    async def test_per_file_has_chunks_reviewed(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={"files": [{"filename": "a.py", "code": "x=1"}]},
            )
        per_file = resp.json()["per_file"][0]
        assert "chunks_reviewed" in per_file
        assert per_file["chunks_reviewed"] >= 1

    async def test_ollama_503_propagated(self, client, mock_review_service):
        mock_review_service.review = AsyncMock(side_effect=RuntimeError("Ollama offline"))
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={"files": [{"filename": "a.py", "code": "x=1"}]},
            )
        assert resp.status_code == 503

    async def test_multi_file_creates_session_with_filenames(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/multi",
                json={
                    "files": [
                        {"filename": "alpha.py", "code": "x=1"},
                        {"filename": "beta.ts", "code": "y=2"},
                    ]
                },
            )
            session_id = resp.json()["session_id"]
            session_resp = await c.get(f"/api/v1/review/sessions/{session_id}")
        body = session_resp.json()
        assert "alpha.py" in (body.get("filename") or "")


class TestSingleFileLanguageAutodetect:
    """Auto-detect language from filename in the single-file route too."""

    async def test_single_review_auto_detects_language(self, client, mock_review_service):
        async with client as c:
            await c.post(
                "/api/v1/review/",
                json={"code": "fn main() {}", "filename": "main.rs"},
            )
        call_kwargs = mock_review_service.review.call_args
        used_lang = call_kwargs.kwargs.get("language") or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
        assert used_lang == "rust"

    async def test_explicit_language_overrides_autodetect(self, client, mock_review_service):
        async with client as c:
            await c.post(
                "/api/v1/review/",
                json={"code": "fn main() {}", "filename": "main.rs", "language": "c"},
            )
        call_kwargs = mock_review_service.review.call_args
        used_lang = call_kwargs.kwargs.get("language") or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
        assert used_lang == "c"
