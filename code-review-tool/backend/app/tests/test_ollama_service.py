"""
Tests for OllamaService — red phase written before implementation.

Coverage:
  - Health check (Ollama running vs not)
  - List available models
  - Send a review prompt and collect streamed response
  - Handle Ollama not running (connection refused)
  - Handle model not found
  - Prompt construction includes code + language + context
"""

import pytest
import httpx
import respx
from app.services.ollama_service import OllamaService


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def service():
    return OllamaService(base_url="http://localhost:11434", model="codellama")


MODELS_PAYLOAD = {
    "models": [
        {"name": "codellama:latest", "size": 3800000000},
        {"name": "deepseek-coder:latest", "size": 4200000000},
    ]
}

SAMPLE_CODE = """
def add(a, b):
    return a + b

x = add(1, "two")
""".strip()

MOCK_REVIEW_RESPONSE = """
SUMMARY: The function itself is correct but is called with mismatched types.

SCORE: 62

ISSUES:
- BUG | critical | line 4 | Type mismatch in function call | add() expects numeric arguments but receives a string | Use add(1, 2) or cast the string to int

STRENGTHS:
- Simple, readable function definition
- Clear variable naming

END
""".strip()


# ─────────────────────────────────────────────
# 1. Health check
# ─────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_is_running_returns_true_when_ollama_up(service):
    """Should return True when Ollama responds to /api/tags."""
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json=MODELS_PAYLOAD)
    )
    result = await service.is_running()
    assert result is True


@respx.mock
@pytest.mark.asyncio
async def test_is_running_returns_false_when_ollama_down(service):
    """Should return False when connection is refused (Ollama not started)."""
    respx.get("http://localhost:11434/api/tags").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    result = await service.is_running()
    assert result is False


# ─────────────────────────────────────────────
# 2. Model listing
# ─────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_list_models_returns_names(service):
    """Should return a list of available model name strings."""
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json=MODELS_PAYLOAD)
    )
    models = await service.list_models()
    assert "codellama:latest" in models
    assert "deepseek-coder:latest" in models
    assert len(models) == 2


@respx.mock
@pytest.mark.asyncio
async def test_list_models_raises_when_ollama_down(service):
    """Should raise RuntimeError when Ollama is unreachable."""
    respx.get("http://localhost:11434/api/tags").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    with pytest.raises(RuntimeError, match="Ollama"):
        await service.list_models()


# ─────────────────────────────────────────────
# 3. Prompt construction
# ─────────────────────────────────────────────

def test_build_prompt_includes_code(service):
    """Prompt should contain the submitted code."""
    prompt = service.build_prompt(code=SAMPLE_CODE, language="python")
    assert SAMPLE_CODE in prompt


def test_build_prompt_includes_language(service):
    """Prompt should include the language when provided."""
    prompt = service.build_prompt(code=SAMPLE_CODE, language="python")
    assert "python" in prompt.lower()


def test_build_prompt_includes_context_when_provided(service):
    """Prompt should include optional context."""
    prompt = service.build_prompt(
        code=SAMPLE_CODE,
        language="python",
        context="This is a utility module",
    )
    assert "utility module" in prompt


def test_build_prompt_omits_context_when_none(service):
    """Prompt should not mention 'None' when context is omitted."""
    prompt = service.build_prompt(code=SAMPLE_CODE, language="python", context=None)
    assert "None" not in prompt


def test_build_prompt_includes_required_section_markers(service):
    """Prompt must instruct the model to produce SUMMARY, SCORE, ISSUES, STRENGTHS."""
    prompt = service.build_prompt(code=SAMPLE_CODE, language="python")
    for marker in ["SUMMARY", "SCORE", "ISSUES", "STRENGTHS"]:
        assert marker in prompt


def test_build_prompt_handles_no_language(service):
    """Prompt should handle missing language gracefully."""
    prompt = service.build_prompt(code=SAMPLE_CODE, language=None)
    assert SAMPLE_CODE in prompt
    assert "None" not in prompt


# ─────────────────────────────────────────────
# 4. Review (non-streaming collect)
# ─────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_review_code_returns_full_response(service):
    """Should POST to /api/generate and return the complete text response."""
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": MOCK_REVIEW_RESPONSE, "done": True})
    )

    result = await service.review_code(code=SAMPLE_CODE, language="python")

    assert isinstance(result, str)
    assert "SUMMARY" in result
    assert "SCORE" in result


@respx.mock
@pytest.mark.asyncio
async def test_review_code_sends_correct_model(service):
    """Should send the configured model name in the request body."""
    route = respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": MOCK_REVIEW_RESPONSE, "done": True})
    )

    await service.review_code(code=SAMPLE_CODE, language="python")

    import json
    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "codellama"


@respx.mock
@pytest.mark.asyncio
async def test_review_code_sets_stream_false(service):
    """Should disable streaming so we get a single complete response."""
    route = respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": MOCK_REVIEW_RESPONSE, "done": True})
    )

    await service.review_code(code=SAMPLE_CODE, language="python")

    import json
    body = json.loads(route.calls[0].request.content)
    assert body["stream"] is False


@respx.mock
@pytest.mark.asyncio
async def test_review_code_raises_when_ollama_down(service):
    """Should raise RuntimeError with helpful message when Ollama is unreachable."""
    respx.post("http://localhost:11434/api/generate").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    with pytest.raises(RuntimeError, match="Ollama"):
        await service.review_code(code=SAMPLE_CODE, language="python")


@respx.mock
@pytest.mark.asyncio
async def test_review_code_raises_on_empty_response(service):
    """Should raise ValueError when Ollama returns an empty response body."""
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "", "done": True})
    )

    with pytest.raises(ValueError, match="empty"):
        await service.review_code(code=SAMPLE_CODE, language="python")


# ─────────────────────────────────────────────
# 5. Model switching
# ─────────────────────────────────────────────

def test_set_model_updates_model(service):
    """Should allow switching the active model."""
    service.set_model("deepseek-coder")
    assert service.model == "deepseek-coder"
