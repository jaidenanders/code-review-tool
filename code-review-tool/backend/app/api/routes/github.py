"""
GitHub API routes.

Endpoints:
  POST /github/auth/device       — Start device flow, returns user_code
  GET  /github/auth/poll         — Poll for token completion
  POST /github/auth/token        — Store token in session (after user confirms)
  GET  /github/repos             — List authenticated user's repos
  GET  /github/repos/{owner}/{repo}/tree   — Get file tree
  GET  /github/repos/{owner}/{repo}/file   — Get file content
"""

import os
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from app.services.github_service import GitHubService
from app.schemas.github import (
    DeviceCodeResponse,
    TokenResponse,
    GitHubRepo,
    FileTreeItem,
    FileContent,
)

router = APIRouter(prefix="/github", tags=["github"])

# In a real app this would be per-user session state in Redis/DB.
# For now, a simple in-memory store keyed by token works for development.
_service_cache: dict[str, GitHubService] = {}
_pending_device_codes: dict[str, str] = {}  # device_code -> client_id


def get_github_client_id() -> str:
    client_id = os.getenv("GITHUB_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_CLIENT_ID environment variable not set.",
        )
    return client_id


def get_service(token: str = Query(..., description="GitHub OAuth token")) -> GitHubService:
    """Dependency: returns an authenticated GitHubService for the given token."""
    if token not in _service_cache:
        svc = GitHubService(client_id=get_github_client_id())
        svc.set_token(token)
        _service_cache[token] = svc
    return _service_cache[token]


# ─────────────────────────────────────────────
# Auth endpoints
# ─────────────────────────────────────────────

@router.post("/auth/device", response_model=DeviceCodeResponse)
async def start_device_flow():
    """
    Initiate GitHub Device Flow OAuth.
    Returns a user_code the user must enter at github.com/login/device.
    """
    client_id = get_github_client_id()
    service = GitHubService(client_id=client_id)

    try:
        result = await service.request_device_code()
        # Store device_code for polling
        _pending_device_codes[result.device_code] = client_id
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub error: {str(e)}")


@router.get("/auth/poll")
async def poll_device_flow(device_code: str = Query(...)):
    """
    Poll GitHub to check if the user has authorized the device.

    Returns:
      { "status": "pending" }  — still waiting
      { "status": "authorized", "token": "gho_..." }  — success
    """
    client_id = _pending_device_codes.get(device_code)
    if not client_id:
        raise HTTPException(status_code=400, detail="Unknown device_code.")

    service = GitHubService(client_id=client_id)

    try:
        result = await service.poll_for_token(device_code)
        if result is None:
            return {"status": "pending"}

        # Clean up pending code
        _pending_device_codes.pop(device_code, None)
        return {"status": "authorized", "token": result.access_token}

    except ValueError as e:
        _pending_device_codes.pop(device_code, None)
        raise HTTPException(status_code=410, detail=str(e))  # 410 Gone = expired
    except PermissionError as e:
        _pending_device_codes.pop(device_code, None)
        raise HTTPException(status_code=403, detail=str(e))


# ─────────────────────────────────────────────
# Repository endpoints
# ─────────────────────────────────────────────

@router.get("/repos", response_model=list[GitHubRepo])
async def list_repos(service: GitHubService = Depends(get_service)):
    """List all repos accessible to the authenticated user."""
    try:
        return await service.list_repos()
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))


@router.get("/repos/{owner}/{repo}/tree", response_model=list[FileTreeItem])
async def get_file_tree(
    owner: str,
    repo: str,
    branch: str = Query("main"),
    service: GitHubService = Depends(get_service),
):
    """Get the full recursive file tree for a repository."""
    full_name = f"{owner}/{repo}"
    try:
        return await service.get_file_tree(full_name, branch)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/repos/{owner}/{repo}/file", response_model=FileContent)
async def get_file_content(
    owner: str,
    repo: str,
    path: str = Query(..., description="File path within the repo"),
    service: GitHubService = Depends(get_service),
):
    """Fetch and decode the content of a single file."""
    full_name = f"{owner}/{repo}"
    try:
        return await service.get_file_content(full_name, path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
