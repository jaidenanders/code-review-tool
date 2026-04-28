"""
Tests for ReviewService — red phase written before implementation.

Coverage:
  - Parse raw Ollama response into structured ReviewResult
  - Handle malformed / partial responses gracefully
  - Orchestrate OllamaService call and return ReviewResult
  - Score clamping (values outside 0-100)
  - Multi-issue parsing
  - Missing optional fields (line number as '?')
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.review_service import ReviewService
from app.schemas.review import ReviewResult, CodeIssue, Severity, IssueCagetory


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def service():
    mock_ollama = MagicMock()
    mock_ollama.review_code = AsyncMock()
    return ReviewService(ollama=mock_ollama)


FULL_RESPONSE = """
SUMMARY: The function is correct but called with mismatched types. Missing input validation.

SCORE: 62

ISSUES:
- bug | critical | line 4 | Type mismatch | add() receives a string argument | Use add(1, 2) or cast: int("two")
- style | info | line ? | No docstring | Function lacks documentation | Add a docstring describing parameters and return value

STRENGTHS:
- Simple, readable function definition
- Clear variable naming

END
""".strip()

MINIMAL_RESPONSE = """
SUMMARY: Code looks reasonable.

SCORE: 80

ISSUES:

STRENGTHS:
- Good structure

END
""".strip()

MALFORMED_NO_SCORE = """
SUMMARY: Something went wrong here.

ISSUES:
- bug | critical | line 1 | Null ref | Value may be None | Add a None check

STRENGTHS:
- Nothing

END
""".strip()

MALFORMED_SCORE_OUT_OF_RANGE = """
SUMMARY: Extremely bad code.

SCORE: 150

ISSUES:

STRENGTHS:

END
""".strip()


# ─────────────────────────────────────────────
# 1. parse_response
# ─────────────────────────────────────────────

def test_parse_returns_review_result(service):
    """parse_response should return a ReviewResult."""
    result = service.parse_response(FULL_RESPONSE)
    assert isinstance(result, ReviewResult)


def test_parse_extracts_summary(service):
    result = service.parse_response(FULL_RESPONSE)
    assert "mismatched types" in result.summary


def test_parse_extracts_score(service):
    result = service.parse_response(FULL_RESPONSE)
    assert result.score == 62


def test_parse_extracts_multiple_issues(service):
    result = service.parse_response(FULL_RESPONSE)
    assert len(result.issues) == 2


def test_parse_issue_fields_correctly(service):
    result = service.parse_response(FULL_RESPONSE)
    bug = result.issues[0]
    assert isinstance(bug, CodeIssue)
    assert bug.category == IssueCagetory.bug
    assert bug.severity == Severity.critical
    assert bug.line == 4
    assert "Type mismatch" in bug.title
    assert "cast" in bug.suggestion


def test_parse_issue_with_unknown_line(service):
    """Line '?' should parse to None."""
    result = service.parse_response(FULL_RESPONSE)
    style_issue = result.issues[1]
    assert style_issue.line is None


def test_parse_extracts_strengths(service):
    result = service.parse_response(FULL_RESPONSE)
    assert len(result.strengths) == 2
    assert any("readable" in s for s in result.strengths)


def test_parse_raw_response_preserved(service):
    """Raw response should be stored verbatim."""
    result = service.parse_response(FULL_RESPONSE)
    assert result.raw_response == FULL_RESPONSE


def test_parse_minimal_response_no_issues(service):
    """Should handle a valid response with no issues."""
    result = service.parse_response(MINIMAL_RESPONSE)
    assert result.issues == []
    assert result.score == 80
    assert len(result.strengths) == 1


def test_parse_clamps_score_above_100(service):
    """Scores above 100 should be clamped to 100."""
    result = service.parse_response(MALFORMED_SCORE_OUT_OF_RANGE)
    assert result.score == 100


def test_parse_defaults_score_when_missing(service):
    """When SCORE is absent, default to 50 (neutral)."""
    result = service.parse_response(MALFORMED_NO_SCORE)
    assert result.score == 50


def test_parse_does_not_raise_on_malformed_issue_line(service):
    """A badly-formed issue line should be skipped, not crash."""
    bad_response = """
SUMMARY: Meh.
SCORE: 55
ISSUES:
- this line is completely malformed garbage
- bug | critical | line 2 | Real issue | Description | Fix it
STRENGTHS:
- Good naming
END
""".strip()
    result = service.parse_response(bad_response)
    # The malformed line is skipped; the valid one is kept
    assert len(result.issues) == 1
    assert result.issues[0].category == IssueCagetory.bug


# ─────────────────────────────────────────────
# 2. review (orchestration)
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_calls_ollama_and_returns_result(service):
    """review() should call ollama.review_code and return a ReviewResult."""
    service.ollama.review_code.return_value = FULL_RESPONSE

    result = await service.review(code="print('hi')", language="python")

    service.ollama.review_code.assert_called_once_with(
        code="print('hi')", language="python", context=None, profile=None
    )
    assert isinstance(result, ReviewResult)
    assert result.score == 62


@pytest.mark.asyncio
async def test_review_passes_context_to_ollama(service):
    """review() should forward optional context to OllamaService."""
    service.ollama.review_code.return_value = FULL_RESPONSE

    await service.review(
        code="x = 1", language="python", context="Global config variable"
    )

    _, kwargs = service.ollama.review_code.call_args
    assert kwargs["context"] == "Global config variable"


@pytest.mark.asyncio
async def test_review_propagates_ollama_runtime_error(service):
    """RuntimeError from OllamaService should bubble up unchanged."""
    service.ollama.review_code.side_effect = RuntimeError("Ollama not reachable")

    with pytest.raises(RuntimeError, match="Ollama"):
        await service.review(code="x = 1", language="python")
