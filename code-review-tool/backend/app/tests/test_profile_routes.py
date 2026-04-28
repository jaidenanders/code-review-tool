"""TDD tests for profile-aware review routes."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db import get_db
from app.services.review_service import ReviewService
from app.schemas.review import ReviewResult, CodeIssue, Severity, IssueCagetory

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.review import Base


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
def good_result():
    return ReviewResult(
        summary="Looks fine.",
        score=75,
        issues=[],
        strengths=["Clean"],
        raw_response="SUMMARY: Looks fine.\nSCORE: 75\nEND",
    )


@pytest.fixture
def mock_review_service(good_result):
    svc = MagicMock(spec=ReviewService)
    svc.review = AsyncMock(return_value=good_result)
    svc.parse_response = MagicMock(return_value=good_result)
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


class TestGetProfiles:
    async def test_get_profiles_returns_200(self, client):
        async with client as c:
            resp = await c.get("/api/v1/review/profiles")
        assert resp.status_code == 200

    async def test_get_profiles_returns_list(self, client):
        async with client as c:
            resp = await c.get("/api/v1/review/profiles")
        assert isinstance(resp.json(), list)

    async def test_get_profiles_returns_four(self, client):
        async with client as c:
            resp = await c.get("/api/v1/review/profiles")
        assert len(resp.json()) == 4

    async def test_profile_objects_have_id_name_description(self, client):
        async with client as c:
            resp = await c.get("/api/v1/review/profiles")
        for p in resp.json():
            assert "id" in p
            assert "name" in p
            assert "description" in p

    async def test_general_is_first(self, client):
        async with client as c:
            resp = await c.get("/api/v1/review/profiles")
        assert resp.json()[0]["id"] == "general"


class TestProfilePassthrough:
    async def test_single_review_accepts_profile_field(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/",
                json={"code": "x = 1", "filename": "a.py", "profile": "security"},
            )
        assert resp.status_code == 200

    async def test_profile_passed_to_review_service(self, client, mock_review_service):
        async with client as c:
            await c.post(
                "/api/v1/review/",
                json={"code": "x = 1", "filename": "a.py", "profile": "performance"},
            )
        call_kwargs = mock_review_service.review.call_args
        used_profile = call_kwargs.kwargs.get("profile") or (
            call_kwargs.args[2] if len(call_kwargs.args) > 2 else None
        )
        assert used_profile == "performance"

    async def test_unknown_profile_still_returns_200(self, client):
        async with client as c:
            resp = await c.post(
                "/api/v1/review/",
                json={"code": "x = 1", "filename": "a.py", "profile": "bogus"},
            )
        assert resp.status_code == 200

    async def test_missing_profile_defaults_to_general(self, client, mock_review_service):
        async with client as c:
            await c.post(
                "/api/v1/review/",
                json={"code": "x = 1", "filename": "a.py"},
            )
        call_kwargs = mock_review_service.review.call_args
        used_profile = call_kwargs.kwargs.get("profile") or (
            call_kwargs.args[2] if len(call_kwargs.args) > 2 else None
        )
        # None or "general" are both acceptable defaults
        assert used_profile in (None, "general")


class TestBuildPromptWithProfile:
    """OllamaService.build_prompt injects focus instructions for non-general profiles."""

    def test_security_profile_adds_focus_to_prompt(self):
        from app.services.ollama_service import OllamaService
        svc = OllamaService()
        prompt = svc.build_prompt("x = 1", "python", profile="security")
        assert "injection" in prompt.lower() or "security" in prompt.lower()

    def test_performance_profile_adds_focus_to_prompt(self):
        from app.services.ollama_service import OllamaService
        svc = OllamaService()
        prompt = svc.build_prompt("x = 1", "python", profile="performance")
        assert "performance" in prompt.lower() or "complex" in prompt.lower()

    def test_style_profile_adds_focus_to_prompt(self):
        from app.services.ollama_service import OllamaService
        svc = OllamaService()
        prompt = svc.build_prompt("x = 1", "python", profile="style")
        assert "style" in prompt.lower() or "nam" in prompt.lower()

    def test_general_profile_produces_same_prompt_as_no_profile(self):
        from app.services.ollama_service import OllamaService
        svc = OllamaService()
        prompt_none = svc.build_prompt("x = 1", "python", profile=None)
        prompt_general = svc.build_prompt("x = 1", "python", profile="general")
        assert prompt_none == prompt_general

    def test_code_still_included_in_profiled_prompt(self):
        from app.services.ollama_service import OllamaService
        svc = OllamaService()
        prompt = svc.build_prompt("SECRET_CODE_HERE", "python", profile="security")
        assert "SECRET_CODE_HERE" in prompt
