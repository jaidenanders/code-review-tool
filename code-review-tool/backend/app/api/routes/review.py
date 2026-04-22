"""
Review & Session API routes.

Endpoints:
  GET  /review/health           — Check if Ollama is running + list models
  POST /review                  — Submit code for review (creates session + review)
  GET  /review/sessions         — List all sessions
  GET  /review/sessions/{id}    — Get session with full review history
  DELETE /review/sessions/{id}  — Delete a session
  GET  /review/sessions/{id}/diff  — Diff between two reviews
"""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, init_db
from app.services.ollama_service import OllamaService
from app.services.review_service import ReviewService
from app.services.session_service import SessionService
from app.schemas.review import (
    ReviewRequest,
    ReviewResult,
    ReviewSession,
    ReviewDiff,
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
# Review submission
# ─────────────────────────────────────────────

@router.post("/", response_model=dict)
async def submit_review(
    request: ReviewRequest,
    session_id: Optional[str] = Query(None, description="Attach to existing session"),
    review_svc: ReviewService = Depends(get_review_service),
    session_svc: SessionService = Depends(get_session_service),
):
    """
    Submit code for review. Creates a new session if none is provided.
    Returns the review result plus session and review IDs for history tracking.
    """
    # Create session if needed
    if session_id is None:
        session_id = await session_svc.create_session(filename=request.filename)

    try:
        result = await review_svc.review(
            code=request.code,
            language=request.language,
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
