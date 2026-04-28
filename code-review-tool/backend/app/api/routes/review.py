"""
Review & Session API routes.

Endpoints:
  GET  /review/health              — Check if Ollama is running + list models
  POST /review/                    — Submit single file for review
  POST /review/stream              — Submit single file for streaming review (SSE)
  POST /review/multi               — Submit multiple files for holistic review
  GET  /review/sessions            — List all sessions
  GET  /review/sessions/{id}       — Get session with full review history
  DELETE /review/sessions/{id}     — Delete a session
  GET  /review/sessions/{id}/diff  — Diff between two reviews
"""

import json
import os
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.ollama_service import OllamaService
from app.services.review_service import ReviewService
from app.services.session_service import SessionService
from app.services.language_service import detect_language
from app.services.chunker_service import chunk_code, format_chunk_for_review
from app.services.aggregator_service import aggregate_results
from app.schemas.review import (
    ReviewRequest,
    ReviewResult,
    ReviewSession,
    ReviewDiff,
    MultiFileReviewRequest,
    FileReviewResult,
)

router = APIRouter(prefix="/review", tags=["review"])

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama")


def get_ollama() -> OllamaService:
    return OllamaService(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)


def get_review_service(ollama: OllamaService = Depends(get_ollama)) -> ReviewService:
    return ReviewService(ollama=ollama)


def get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db=db)


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────

@router.get("/health")
async def review_health(ollama: OllamaService = Depends(get_ollama)):
    """Check if Ollama is running and return available models."""
    running = await ollama.is_running()
    if not running:
        return {
            "ollama": "offline",
            "models": [],
            "hint": "Run `ollama serve` to start Ollama.",
        }
    models = await ollama.list_models()
    return {"ollama": "online", "models": models, "active_model": ollama.model}


# ─────────────────────────────────────────────
# Single-file review
# ─────────────────────────────────────────────

@router.post("/", response_model=dict)
async def submit_review(
    request: ReviewRequest,
    session_id: Optional[str] = Query(None, description="Attach to existing session"),
    review_svc: ReviewService = Depends(get_review_service),
    session_svc: SessionService = Depends(get_session_service),
):
    """Submit code for review.  Language is auto-detected from *filename* when
    the caller omits the *language* field."""
    if session_id is None:
        session_id = await session_svc.create_session(filename=request.filename)

    # Auto-detect language from filename when not explicitly provided
    language = request.language
    if not language and request.filename:
        language = detect_language(request.filename)
        if language == "unknown":
            language = None

    try:
        result = await review_svc.review(
            code=request.code,
            language=language,
            context=request.context,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        review_id = await session_svc.save_review(
            session_id=session_id, code=request.code, result=result
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "session_id": session_id,
        "review_id": review_id,
        "result": result.model_dump(),
    }


# ─────────────────────────────────────────────
# Streaming review (SSE)
# ─────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
async def stream_review(
    request: ReviewRequest,
    session_id: Optional[str] = Query(None, description="Attach to existing session"),
    ollama: OllamaService = Depends(get_ollama),
    review_svc: ReviewService = Depends(get_review_service),
    session_svc: SessionService = Depends(get_session_service),
):
    """Stream review tokens via Server-Sent Events.

    Emits:
      ``event: token``  — one per LLM token, ``data: {"text": "..."}``
      ``event: result`` — final parsed result with session/review IDs
      ``event: error``  — if Ollama is unreachable, ``data: {"message": "..."}``
    """
    if session_id is None:
        session_id = await session_svc.create_session(filename=request.filename)

    language = request.language
    if not language and request.filename:
        language = detect_language(request.filename)
        if language == "unknown":
            language = None

    async def event_stream() -> AsyncGenerator[str, None]:
        accumulated = []
        try:
            async for token in ollama.stream_review_code(
                code=request.code,
                language=language,
                context=request.context,
            ):
                accumulated.append(token)
                yield _sse("token", {"text": token})
        except RuntimeError as exc:
            yield _sse("error", {"message": str(exc)})
            return

        raw = "".join(accumulated)
        try:
            result = review_svc.parse_response(raw)
        except Exception:
            result = review_svc.parse_response("")

        try:
            review_id = await session_svc.save_review(
                session_id=session_id, code=request.code, result=result
            )
        except ValueError:
            review_id = ""

        yield _sse("result", {
            "session_id": session_id,
            "review_id": review_id,
            "result": result.model_dump(),
        })

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ─────────────────────────────────────────────
# Multi-file review
# ─────────────────────────────────────────────

@router.post("/multi", response_model=dict)
async def submit_multi_file_review(
    request: MultiFileReviewRequest,
    session_id: Optional[str] = Query(None, description="Attach to existing session"),
    review_svc: ReviewService = Depends(get_review_service),
    session_svc: SessionService = Depends(get_session_service),
):
    """Review multiple files as a cohesive module.

    Each file is:
    1. Language-detected from its extension.
    2. Split into context-window-safe chunks at logical boundaries.
    3. Reviewed chunk-by-chunk.
    4. Per-file results are aggregated, then all files are aggregated into
       one final :class:`ReviewResult`.
    """
    filenames = ", ".join(f.filename for f in request.files)
    if session_id is None:
        session_id = await session_svc.create_session(filename=filenames)

    per_file_results: list[FileReviewResult] = []

    for file_input in request.files:
        language = detect_language(file_input.filename)
        effective_language = None if language == "unknown" else language

        chunks = chunk_code(
            code=file_input.code,
            filename=file_input.filename,
            language=language,
        )

        chunk_results: list[ReviewResult] = []
        for chunk in chunks:
            prompt_code = format_chunk_for_review(chunk)
            try:
                result = await review_svc.review(
                    code=prompt_code,
                    language=effective_language,
                    context=request.context,
                )
            except RuntimeError as e:
                raise HTTPException(status_code=503, detail=str(e))
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
            chunk_results.append(result)

        # Aggregate chunk results weighted by chunk size
        chunk_weights = [float(len(c.content)) for c in chunks]
        file_result = aggregate_results(chunk_results, chunk_weights)

        per_file_results.append(
            FileReviewResult(
                filename=file_input.filename,
                language=language,
                result=file_result,
                chunks_reviewed=len(chunks),
            )
        )

    # Aggregate all files weighted by their code size
    file_weights = [float(len(f.code)) for f in request.files]
    final_result = aggregate_results(
        [pfr.result for pfr in per_file_results],
        file_weights,
    )

    # Save one combined review snapshot to the session
    combined_code = "\n\n---\n\n".join(
        f"# {f.filename}\n{f.code}" for f in request.files
    )
    try:
        review_id = await session_svc.save_review(
            session_id=session_id, code=combined_code, result=final_result
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    total_chunks = sum(pfr.chunks_reviewed for pfr in per_file_results)

    return {
        "session_id": session_id,
        "review_id": review_id,
        "result": final_result.model_dump(),
        "per_file": [pfr.model_dump() for pfr in per_file_results],
        "total_chunks": total_chunks,
    }


# ─────────────────────────────────────────────
# Session management
# ─────────────────────────────────────────────

@router.get("/sessions", response_model=list[ReviewSession])
async def list_sessions(session_svc: SessionService = Depends(get_session_service)):
    """List all review sessions, newest first."""
    return await session_svc.list_sessions()


@router.get("/sessions/{session_id}", response_model=ReviewSession)
async def get_session(
    session_id: str,
    session_svc: SessionService = Depends(get_session_service),
):
    """Get a session with its full review history."""
    session = await session_svc.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return session


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    session_svc: SessionService = Depends(get_session_service),
):
    """Delete a session and all its reviews."""
    await session_svc.delete_session(session_id)


@router.get("/sessions/{session_id}/diff", response_model=ReviewDiff)
async def get_diff(
    session_id: str,
    review_a: str = Query(..., description="ID of the earlier review"),
    review_b: str = Query(..., description="ID of the later review"),
    session_svc: SessionService = Depends(get_session_service),
):
    """Generate a line-level diff between two reviews in a session."""
    try:
        return await session_svc.get_diff(
            session_id=session_id,
            review_a_id=review_a,
            review_b_id=review_b,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
