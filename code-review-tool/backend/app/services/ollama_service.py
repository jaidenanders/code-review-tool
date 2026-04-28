"""
OllamaService — communicates with a locally-running Ollama instance.

Responsibilities:
  - Health check (is Ollama running?)
  - List available models
  - Build structured review prompts
  - Send code for review and collect the full response
  - Stream code review tokens as an async generator
"""

from typing import Optional, AsyncGenerator
import json
import httpx


class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "codellama"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def set_model(self, model: str) -> None:
        self.model = model

    # ─────────────────────────────────────────
    # Health & discovery
    # ─────────────────────────────────────────

    async def is_running(self) -> bool:
        """Return True if Ollama is reachable, False otherwise."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[str]:
        """Return the names of all locally available models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise RuntimeError(
                f"Ollama is not reachable at {self.base_url}. "
                "Make sure Ollama is running (`ollama serve`)."
            ) from e

    # ─────────────────────────────────────────
    # Prompt construction
    # ─────────────────────────────────────────

    def build_prompt(
        self,
        code: str,
        language: Optional[str],
        context: Optional[str] = None,
    ) -> str:
        """
        Build a structured prompt that instructs the model to return
        a parseable review in a specific format.
        """
        lang_line = f"Language: {language}" if language else "Language: unknown"
        context_line = f"Context: {context}\n" if context else ""

        return f"""You are an expert code reviewer. Analyze the following code and respond in EXACTLY this format — no extra commentary before or after:

SUMMARY: <one paragraph summary of overall code quality>

SCORE: <integer 0-100 representing overall quality>

ISSUES:
- <CATEGORY> | <SEVERITY> | line <N or ?> | <title> | <description> | <suggestion>
(Repeat one line per issue. CATEGORY: bug|complexity|security|style|performance. SEVERITY: critical|warning|info)

STRENGTHS:
- <one strength per line>

END

{lang_line}
{context_line}
Code to review:
```
{code}
```"""

    # ─────────────────────────────────────────
    # Review
    # ─────────────────────────────────────────

    async def review_code(
        self,
        code: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        Send code to Ollama for review and return the full response string.

        Args:
            code: Source code to review
            language: Programming language hint
            context: Optional free-text context about the code

        Returns:
            Raw string response from the model

        Raises:
            RuntimeError: If Ollama is unreachable
            ValueError: If the model returns an empty response
        """
        prompt = self.build_prompt(code=code, language=language, context=context)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise RuntimeError(
                f"Ollama is not reachable at {self.base_url}. "
                "Make sure Ollama is running (`ollama serve`)."
            ) from e

        data = resp.json()
        response_text = data.get("response", "").strip()

        if not response_text:
            raise ValueError("Ollama returned an empty response. Try a different model or prompt.")

        return response_text

    # ─────────────────────────────────────────
    # Streaming review
    # ─────────────────────────────────────────

    async def stream_review_code(
        self,
        code: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream code review tokens from Ollama one at a time.

        Yields each non-empty ``response`` field from the NDJSON stream.
        Stops when ``done`` is ``True``.

        Raises:
            RuntimeError: If Ollama is unreachable or times out.
        """
        prompt = self.build_prompt(code=code, language=language, context=context)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": True,
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise RuntimeError(
                f"Ollama is not reachable at {self.base_url}. "
                "Make sure Ollama is running (`ollama serve`)."
            ) from e
