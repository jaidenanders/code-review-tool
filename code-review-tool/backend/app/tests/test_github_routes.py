"""
Integration tests for GitHub API routes.

Uses FastAPI's TestClient + respx to mock upstream GitHub calls.
Tests the full request/response cycle including error mapping.
"""

import pytest
import httpx
import respx
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.api.routes import github as github_module

client = TestClient(app)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

VALID_TOKEN = "gho_testtoken123"
BASE = "/api/v1/github"

DEVICE_CODE_PAYLOAD = {
    "device_code": "dev_abc123",
    "user_code": "ABCD-1234",
    "verification_uri": "https://github.com/login/device",
    "expires_in": 900,
    "interval": 5,
}

REPOS_PAYLOAD = [
    {
        "id": 1,
        "name": "my-project",
        "full_name": "jaiden/my-project",
        "private": False,
        "description": "A cool project",
        "language": "Python",
        "default_branch": "main",
        "updated_at": "2025-01-01T00:00:00Z",
    }
]

FILE_TREE_PAYLOAD = {
    "tree": [
        {"path": "README.md", "type": "blob", "size": 1024, "sha": "abc"},
        {"path": "src/main.py", "type": "blob", "size": 2048, "sha": "ghi"},
    ]
}

FILE_CONTENT_PAYLOAD = {
    "path": "src/main.py",
    "content": "cHJpbnQoJ2hlbGxvJyk=",
    "encoding": "base64",
    "size": 16,
    "sha": "ghi",
}


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ─────────────────────────────────────────────
# POST /github/auth/device
# ─────────────────────────────────────────────

@respx.mock
def test_start_device_flow_returns_200(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    respx.post("https://github.com/login/device/code").mock(
        return_value=httpx.Response(200, json=DEVICE_CODE_PAYLOAD)
    )

    response = client.post(f"{BASE}/auth/device")

    assert response.status_code == 200
    data = response.json()
    assert data["user_code"] == "ABCD-1234"
    assert data["verification_uri"] == "https://github.com/login/device"


def test_start_device_flow_500_without_client_id(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)

    response = client.post(f"{BASE}/auth/device")

    assert response.status_code == 500
    assert "GITHUB_CLIENT_ID" in response.json()["detail"]


# ─────────────────────────────────────────────
# GET /github/auth/poll
# ─────────────────────────────────────────────

@respx.mock
def test_poll_returns_pending_when_waiting(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    # Seed a pending device code
    github_module._pending_device_codes["dev_abc123"] = "test-client-id"

    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"error": "authorization_pending"})
    )

    response = client.get(f"{BASE}/auth/poll?device_code=dev_abc123")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


@respx.mock
def test_poll_returns_authorized_with_token(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    github_module._pending_device_codes["dev_abc123"] = "test-client-id"

    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "gho_realtoken456",
            "token_type": "bearer",
            "scope": "repo",
        })
    )

    response = client.get(f"{BASE}/auth/poll?device_code=dev_abc123")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "authorized"
    assert data["token"] == "gho_realtoken456"


def test_poll_returns_400_for_unknown_device_code():
    response = client.get(f"{BASE}/auth/poll?device_code=unknown_code")
    assert response.status_code == 400


@respx.mock
def test_poll_returns_410_when_expired(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    github_module._pending_device_codes["dev_expired"] = "test-client-id"

    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"error": "expired_token"})
    )

    response = client.get(f"{BASE}/auth/poll?device_code=dev_expired")
    assert response.status_code == 410


# ─────────────────────────────────────────────
# GET /github/repos
# ─────────────────────────────────────────────

@respx.mock
def test_list_repos_returns_200(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    respx.get("https://api.github.com/user/repos").mock(
        return_value=httpx.Response(200, json=REPOS_PAYLOAD)
    )

    response = client.get(f"{BASE}/repos?token={VALID_TOKEN}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "my-project"


@respx.mock
def test_list_repos_returns_429_on_rate_limit(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    respx.get("https://api.github.com/user/repos").mock(
        return_value=httpx.Response(403, json={"message": "API rate limit exceeded"})
    )

    response = client.get(f"{BASE}/repos?token={VALID_TOKEN}")
    assert response.status_code == 429


# ─────────────────────────────────────────────
# GET /github/repos/{owner}/{repo}/tree
# ─────────────────────────────────────────────

@respx.mock
def test_get_file_tree_returns_200(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    respx.get(
        "https://api.github.com/repos/jaiden/my-project/git/trees/main"
    ).mock(return_value=httpx.Response(200, json=FILE_TREE_PAYLOAD))

    response = client.get(
        f"{BASE}/repos/jaiden/my-project/tree?token={VALID_TOKEN}&branch=main"
    )

    assert response.status_code == 200
    tree = response.json()
    assert len(tree) == 2
    assert tree[0]["path"] == "README.md"


@respx.mock
def test_get_file_tree_returns_404_for_missing_repo(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    respx.get(
        "https://api.github.com/repos/jaiden/ghost/git/trees/main"
    ).mock(return_value=httpx.Response(404, json={"message": "Not Found"}))

    response = client.get(
        f"{BASE}/repos/jaiden/ghost/tree?token={VALID_TOKEN}&branch=main"
    )
    assert response.status_code == 404


# ─────────────────────────────────────────────
# GET /github/repos/{owner}/{repo}/file
# ─────────────────────────────────────────────

@respx.mock
def test_get_file_content_returns_decoded_content(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    respx.get(
        "https://api.github.com/repos/jaiden/my-project/contents/src/main.py"
    ).mock(return_value=httpx.Response(200, json=FILE_CONTENT_PAYLOAD))

    response = client.get(
        f"{BASE}/repos/jaiden/my-project/file"
        f"?token={VALID_TOKEN}&path=src/main.py"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "print('hello')"
    assert data["path"] == "src/main.py"


@respx.mock
def test_get_file_content_returns_400_for_directory(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    respx.get(
        "https://api.github.com/repos/jaiden/my-project/contents/src"
    ).mock(return_value=httpx.Response(200, json=[
        {"name": "main.py", "type": "file"}
    ]))

    response = client.get(
        f"{BASE}/repos/jaiden/my-project/file"
        f"?token={VALID_TOKEN}&path=src"
    )
    assert response.status_code == 400


@respx.mock
def test_get_file_content_returns_404_for_missing_file(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    respx.get(
        "https://api.github.com/repos/jaiden/my-project/contents/missing.py"
    ).mock(return_value=httpx.Response(404, json={"message": "Not Found"}))

    response = client.get(
        f"{BASE}/repos/jaiden/my-project/file"
        f"?token={VALID_TOKEN}&path=missing.py"
    )
    assert response.status_code == 404
