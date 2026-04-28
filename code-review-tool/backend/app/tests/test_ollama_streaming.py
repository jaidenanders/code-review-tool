"""TDD tests for OllamaService.stream_review_code — token-by-token streaming."""
import json
import pytest
import httpx
import respx
from app.services.ollama_service import OllamaService

SAMPLE_CODE = "def add(a, b): return a + b"

# Simulated Ollama NDJSON streaming response
STREAM_LINES = [
    json.dumps({"response": "SUMMARY", "done": False}),
    json.dumps({"response": ": looks good\n", "done": False}),
    json.dumps({"response": "SCORE: 80\n", "done": False}),
    json.dumps({"response": "ISSUES:\n", "done": False}),
    json.dumps({"response": "STRENGTHS:\n- Clean\nEND", "done": False}),
    json.dumps({"response": "", "done": True}),
]
STREAM_BODY = "\n".join(STREAM_LINES)


@pytest.fixture
def service():
    return OllamaService(base_url="http://localhost:11434", model="codellama")


@respx.mock
@pytest.mark.asyncio
async def test_stream_yields_non_empty_tokens(service):
    """Should yield each non-empty token string from the NDJSON stream."""
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, text=STREAM_BODY)
    )
    tokens = []
    async for token in service.stream_review_code(SAMPLE_CODE, "python"):
        tokens.append(token)

    assert len(tokens) > 0
    assert all(isinstance(t, str) for t in tokens)


@respx.mock
@pytest.mark.asyncio
async def test_stream_does_not_yield_empty_tokens(service):
    """Empty response fields (e.g. the final done:true line) should not be yielded."""
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, text=STREAM_BODY)
    )
    tokens = []
    async for token in service.stream_review_code(SAMPLE_CODE, "python"):
        tokens.append(token)

    assert all(t != "" for t in tokens)


@respx.mock
@pytest.mark.asyncio
async def test_stream_full_text_reconstructable(service):
    """Concatenating all yielded tokens should reproduce the full model output."""
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, text=STREAM_BODY)
    )
    tokens = []
    async for token in service.stream_review_code(SAMPLE_CODE, "python"):
        tokens.append(token)

    full = "".join(tokens)
    assert "SUMMARY" in full
    assert "SCORE" in full
    assert "STRENGTHS" in full


@respx.mock
@pytest.mark.asyncio
async def test_stream_sends_stream_true_in_body(service):
    """Request to Ollama must include stream: true."""
    route = respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, text=STREAM_BODY)
    )
    async for _ in service.stream_review_code(SAMPLE_CODE, "python"):
        pass

    body = json.loads(route.calls[0].request.content)
    assert body["stream"] is True


@respx.mock
@pytest.mark.asyncio
async def test_stream_sends_correct_model(service):
    route = respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, text=STREAM_BODY)
    )
    async for _ in service.stream_review_code(SAMPLE_CODE, "python"):
        pass

    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "codellama"


@respx.mock
@pytest.mark.asyncio
async def test_stream_includes_language_in_prompt(service):
    route = respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, text=STREAM_BODY)
    )
    async for _ in service.stream_review_code(SAMPLE_CODE, "python"):
        pass

    body = json.loads(route.calls[0].request.content)
    assert "python" in body["prompt"].lower()


@respx.mock
@pytest.mark.asyncio
async def test_stream_raises_runtime_error_when_ollama_down(service):
    """Should raise RuntimeError when Ollama is unreachable."""
    respx.post("http://localhost:11434/api/generate").mock(
        side_effect=httpx.ConnectError("refused")
    )
    with pytest.raises(RuntimeError, match="Ollama"):
        async for _ in service.stream_review_code(SAMPLE_CODE, "python"):
            pass


@respx.mock
@pytest.mark.asyncio
async def test_stream_raises_on_timeout(service):
    respx.post("http://localhost:11434/api/generate").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    with pytest.raises(RuntimeError):
        async for _ in service.stream_review_code(SAMPLE_CODE, "python"):
            pass


@respx.mock
@pytest.mark.asyncio
async def test_stream_stops_after_done_true(service):
    """Must stop yielding after the Ollama done:true sentinel line."""
    extra_lines = STREAM_LINES + [
        json.dumps({"response": "SHOULD NOT APPEAR", "done": False}),
    ]
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, text="\n".join(extra_lines))
    )
    tokens = []
    async for token in service.stream_review_code(SAMPLE_CODE, "python"):
        tokens.append(token)

    assert "SHOULD NOT APPEAR" not in "".join(tokens)


@respx.mock
@pytest.mark.asyncio
async def test_stream_works_with_no_language(service):
    """Streaming should work when language is None."""
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, text=STREAM_BODY)
    )
    tokens = []
    async for token in service.stream_review_code(SAMPLE_CODE, None):
        tokens.append(token)
    assert len(tokens) > 0
