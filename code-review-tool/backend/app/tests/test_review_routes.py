"""
Integration tests for review & session API routes.

Uses FastAPI TestClient with:
  - In-memory SQLite for the DB layer (injected via dependency override)
  - Mocked OllamaService so no real Ollama instance is needed
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db import get_db
from app.models.review import Base
from app.services.review_service import ReviewService
from app.services.session_service import SessionService
from app.api.routes.review import get_review_service, get_session_service
from app.schemas.review import ReviewResult, CodeIssue, Severity, IssueCagetory

# ─────────────────────────────────────────────
# In-memory DB shared across all route tests
# ─────────────────────────────────────────────

TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
TestSessionFactory = async_sessionmaker(
    TEST_ENGINE, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestSessionFactory() as session:
        yield session


# ─────────────────────────────────────────────
# Mock ReviewService (no real Ollama needed)
# ─────────────────────────────────────────────

MOCK_RESULT = ReviewResult(
    summary="Code looks solid with a minor type issue.",
    score=74,
    issues=[
        CodeIssue(
            category=IssueCagetory.bug,
            severity=Severity.warning,
            line=3,
            title="Type mismatch",
            description="String passed where int expected",
            suggestion="Cast to int or fix the call site",
        )
    ],
    strengths=["Clean structure", "Good naming"],
    raw_response="SUMMARY: Code looks solid...\nSCORE: 74\n...",
)


def make_mock_review_service():
    svc = MagicMock(spec=ReviewService)
    svc.review = AsyncMock(return_value=MOCK_RESULT)
    return svc


def make_real_session_service(db):
    return SessionService(db=db)


# ─────────────────────────────────────────────
# Client fixture — sets up DB + overrides
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    import asyncio

    async def setup():
        async with TEST_ENGINE.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup())

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_review_service] = make_mock_review_service

    async def override_session_svc():
        async with TestSessionFactory() as db:
            yield SessionService(db=db)

    app.dependency_overrides[get_session_service] = override_session_svc

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


BASE = "/api/v1/review"


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────

def test_review_health_ollama_offline(client):
    """Health endpoint should report offline if Ollama isn't running."""
    with patch(
        "app.api.routes.review.OllamaService.is_running",
        new=AsyncMock(return_value=False),
    ):
        resp = client.get(f"{BASE}/health")
    assert resp.status_code == 200
    assert resp.json()["ollama"] == "offline"


def test_review_health_ollama_online(client):
    with patch(
        "app.api.routes.review.OllamaService.is_running",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.api.routes.review.OllamaService.list_models",
        new=AsyncMock(return_value=["codellama:latest"]),
    ):
        resp = client.get(f"{BASE}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ollama"] == "online"
    assert "codellama:latest" in data["models"]


# ─────────────────────────────────────────────
# POST /review/
# ─────────────────────────────────────────────

def test_submit_review_returns_200(client):
    resp = client.post(f"{BASE}/", json={
        "code": "def add(a, b): return a + b",
        "language": "python",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "review_id" in data
    assert data["result"]["score"] == 74


def test_submit_review_creates_session(client):
    """Each submission without a session_id should create a new session."""
    r1 = client.post(f"{BASE}/", json={"code": "x = 1", "language": "python"})
    r2 = client.post(f"{BASE}/", json={"code": "y = 2", "language": "python"})
    assert r1.json()["session_id"] != r2.json()["session_id"]


def test_submit_review_appends_to_existing_session(client):
    """Submitting with an existing session_id should reuse it."""
    r1 = client.post(f"{BASE}/", json={"code": "x = 1", "language": "python"})
    session_id = r1.json()["session_id"]

    r2 = client.post(
        f"{BASE}/",
        params={"session_id": session_id},
        json={"code": "x = 2", "language": "python"},
    )
    assert r2.status_code == 200
    assert r2.json()["session_id"] == session_id


def test_submit_review_503_when_ollama_down(client):
    """Should return 503 when OllamaService raises RuntimeError."""
    mock_svc = MagicMock(spec=ReviewService)
    mock_svc.review = AsyncMock(side_effect=RuntimeError("Ollama not reachable"))

    app.dependency_overrides[get_review_service] = lambda: mock_svc
    resp = client.post(f"{BASE}/", json={"code": "x = 1", "language": "python"})
    app.dependency_overrides[get_review_service] = make_mock_review_service

    assert resp.status_code == 503


def test_submit_review_includes_filename(client):
    resp = client.post(f"{BASE}/", json={
        "code": "x = 1",
        "language": "python",
        "filename": "utils.py",
    })
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    session_resp = client.get(f"{BASE}/sessions/{session_id}")
    assert session_resp.json()["filename"] == "utils.py"


# ─────────────────────────────────────────────
# GET /review/sessions
# ─────────────────────────────────────────────

def test_list_sessions_returns_array(client):
    resp = client.get(f"{BASE}/sessions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_sessions_includes_submitted_sessions(client):
    client.post(f"{BASE}/", json={"code": "z = 99", "language": "python", "filename": "z.py"})
    resp = client.get(f"{BASE}/sessions")
    filenames = [s.get("filename") for s in resp.json()]
    assert "z.py" in filenames


# ─────────────────────────────────────────────
# GET /review/sessions/{id}
# ─────────────────────────────────────────────

def test_get_session_returns_reviews(client):
    r = client.post(f"{BASE}/", json={"code": "a = 1", "language": "python"})
    session_id = r.json()["session_id"]

    resp = client.get(f"{BASE}/sessions/{session_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == session_id
    assert len(data["reviews"]) >= 1
    assert data["reviews"][0]["result"]["score"] == 74


def test_get_session_404_for_missing(client):
    resp = client.get(f"{BASE}/sessions/nonexistent-id")
    assert resp.status_code == 404


# ─────────────────────────────────────────────
# DELETE /review/sessions/{id}
# ─────────────────────────────────────────────

def test_delete_session_returns_204(client):
    r = client.post(f"{BASE}/", json={"code": "del_me = 1", "language": "python"})
    session_id = r.json()["session_id"]

    resp = client.delete(f"{BASE}/sessions/{session_id}")
    assert resp.status_code == 204


def test_delete_session_removes_it(client):
    r = client.post(f"{BASE}/", json={"code": "del_me2 = 1", "language": "python"})
    session_id = r.json()["session_id"]

    client.delete(f"{BASE}/sessions/{session_id}")
    assert client.get(f"{BASE}/sessions/{session_id}").status_code == 404


# ─────────────────────────────────────────────
# GET /review/sessions/{id}/diff
# ─────────────────────────────────────────────

def test_diff_returns_score_delta_and_lines(client):
    """Two reviews in same session should produce a valid diff."""
    r1 = client.post(f"{BASE}/", json={"code": "def f(a):\n    return a", "language": "python"})
    session_id = r1.json()["session_id"]
    rev_a = r1.json()["review_id"]

    r2 = client.post(
        f"{BASE}/",
        params={"session_id": session_id},
        json={"code": "def f(a: int) -> int:\n    \"\"\"Typed.\"\"\"\n    return a", "language": "python"},
    )
    rev_b = r2.json()["review_id"]

    resp = client.get(
        f"{BASE}/sessions/{session_id}/diff",
        params={"review_a": rev_a, "review_b": rev_b},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "score_delta" in data
    assert "lines" in data
    assert len(data["lines"]) > 0


def test_diff_404_for_unknown_review(client):
    r = client.post(f"{BASE}/", json={"code": "x = 1", "language": "python"})
    session_id = r.json()["session_id"]
    rev_a = r.json()["review_id"]

    resp = client.get(
        f"{BASE}/sessions/{session_id}/diff",
        params={"review_a": rev_a, "review_b": "bad-id"},
    )
    assert resp.status_code == 404
