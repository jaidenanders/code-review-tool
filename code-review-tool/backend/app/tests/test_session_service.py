"""
Tests for SessionService — red phase written before implementation.

Uses an in-memory SQLite database so tests are fast and fully isolated.

Coverage:
  - Create a session
  - Save a review to a session
  - List all sessions (most recent first)
  - Get a specific session with its reviews
  - Delete a session and its reviews
  - Generate a diff between two reviews in a session
  - Handle missing session gracefully
"""

import json
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models.review import Base
from app.services.session_service import SessionService
from app.schemas.review import ReviewResult, CodeIssue, Severity, IssueCagetory


# ─────────────────────────────────────────────
# In-memory DB setup for tests
# ─────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    """Provide a clean in-memory SQLite session for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def svc(db_session):
    return SessionService(db=db_session)


# ─────────────────────────────────────────────
# Sample data helpers
# ─────────────────────────────────────────────

def make_result(score=75, summary="Looks good") -> ReviewResult:
    return ReviewResult(
        summary=summary,
        score=score,
        issues=[
            CodeIssue(
                category=IssueCagetory.bug,
                severity=Severity.warning,
                line=3,
                title="Possible null dereference",
                description="Value may be None",
                suggestion="Add a None check",
            )
        ],
        strengths=["Clean structure"],
        raw_response=f"SUMMARY: {summary}\nSCORE: {score}\n...",
    )


CODE_V1 = "def add(a, b):\n    return a + b"
CODE_V2 = "def add(a: int, b: int) -> int:\n    \"\"\"Add two integers.\"\"\"\n    return a + b"


# ─────────────────────────────────────────────
# 1. Create session
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_session_returns_id(svc):
    """create_session should return a non-empty string ID."""
    session_id = await svc.create_session(filename="main.py")
    assert isinstance(session_id, str)
    assert len(session_id) > 0


@pytest.mark.asyncio
async def test_create_session_stores_filename(svc):
    session_id = await svc.create_session(filename="utils.py")
    session = await svc.get_session(session_id)
    assert session.filename == "utils.py"


@pytest.mark.asyncio
async def test_create_session_stores_repo(svc):
    session_id = await svc.create_session(repo="jaiden/my-project")
    session = await svc.get_session(session_id)
    assert session.repo == "jaiden/my-project"


@pytest.mark.asyncio
async def test_create_session_without_metadata(svc):
    """Should work with no filename or repo."""
    session_id = await svc.create_session()
    session = await svc.get_session(session_id)
    assert session.filename is None
    assert session.repo is None


# ─────────────────────────────────────────────
# 2. Save review
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_review_returns_review_id(svc):
    session_id = await svc.create_session(filename="main.py")
    review_id = await svc.save_review(
        session_id=session_id, code=CODE_V1, result=make_result()
    )
    assert isinstance(review_id, str)
    assert len(review_id) > 0


@pytest.mark.asyncio
async def test_save_review_appears_in_session(svc):
    session_id = await svc.create_session(filename="main.py")
    await svc.save_review(session_id=session_id, code=CODE_V1, result=make_result(score=70))

    session = await svc.get_session(session_id)
    assert len(session.reviews) == 1
    assert session.reviews[0].result.score == 70


@pytest.mark.asyncio
async def test_save_multiple_reviews_ordered_by_time(svc):
    """Reviews should come back in chronological order."""
    session_id = await svc.create_session(filename="main.py")
    await svc.save_review(session_id=session_id, code=CODE_V1, result=make_result(score=60))
    await svc.save_review(session_id=session_id, code=CODE_V2, result=make_result(score=85))

    session = await svc.get_session(session_id)
    assert len(session.reviews) == 2
    assert session.reviews[0].result.score == 60
    assert session.reviews[1].result.score == 85


@pytest.mark.asyncio
async def test_save_review_raises_for_unknown_session(svc):
    with pytest.raises(ValueError, match="Session not found"):
        await svc.save_review(
            session_id="nonexistent-id", code=CODE_V1, result=make_result()
        )


# ─────────────────────────────────────────────
# 3. List sessions
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sessions_returns_all(svc):
    await svc.create_session(filename="a.py")
    await svc.create_session(filename="b.py")
    await svc.create_session(filename="c.py")

    sessions = await svc.list_sessions()
    assert len(sessions) == 3


@pytest.mark.asyncio
async def test_list_sessions_most_recent_first(svc):
    """Sessions should be ordered newest first."""
    id_a = await svc.create_session(filename="a.py")
    id_b = await svc.create_session(filename="b.py")

    sessions = await svc.list_sessions()
    assert sessions[0].id == id_b
    assert sessions[1].id == id_a


@pytest.mark.asyncio
async def test_list_sessions_empty_when_none(svc):
    sessions = await svc.list_sessions()
    assert sessions == []


# ─────────────────────────────────────────────
# 4. Get session
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_session_returns_none_for_missing(svc):
    result = await svc.get_session("nonexistent-id")
    assert result is None


# ─────────────────────────────────────────────
# 5. Delete session
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_session_removes_it(svc):
    session_id = await svc.create_session(filename="temp.py")
    await svc.delete_session(session_id)
    assert await svc.get_session(session_id) is None


@pytest.mark.asyncio
async def test_delete_session_removes_its_reviews(svc):
    session_id = await svc.create_session(filename="temp.py")
    await svc.save_review(session_id=session_id, code=CODE_V1, result=make_result())
    await svc.delete_session(session_id)
    assert await svc.get_session(session_id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_session_does_not_raise(svc):
    """Deleting a session that doesn't exist should be a no-op."""
    await svc.delete_session("nonexistent-id")  # should not raise


# ─────────────────────────────────────────────
# 6. Diff between reviews
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_diff_returns_score_delta(svc):
    session_id = await svc.create_session(filename="main.py")
    rev_a = await svc.save_review(session_id=session_id, code=CODE_V1, result=make_result(score=60))
    rev_b = await svc.save_review(session_id=session_id, code=CODE_V2, result=make_result(score=85))

    diff = await svc.get_diff(session_id=session_id, review_a_id=rev_a, review_b_id=rev_b)
    assert diff.score_delta == 25


@pytest.mark.asyncio
async def test_diff_contains_lines(svc):
    session_id = await svc.create_session(filename="main.py")
    rev_a = await svc.save_review(session_id=session_id, code=CODE_V1, result=make_result(score=60))
    rev_b = await svc.save_review(session_id=session_id, code=CODE_V2, result=make_result(score=85))

    diff = await svc.get_diff(session_id=session_id, review_a_id=rev_a, review_b_id=rev_b)
    assert len(diff.lines) > 0
    change_types = {line.change_type for line in diff.lines}
    assert "added" in change_types  # CODE_V2 has new lines


@pytest.mark.asyncio
async def test_diff_raises_for_unknown_review(svc):
    session_id = await svc.create_session(filename="main.py")
    rev_a = await svc.save_review(session_id=session_id, code=CODE_V1, result=make_result())

    with pytest.raises(ValueError, match="Review not found"):
        await svc.get_diff(
            session_id=session_id, review_a_id=rev_a, review_b_id="bad-id"
        )
