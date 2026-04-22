"""
Tests for GitHubService — written before implementation (TDD red phase).

Coverage:
  - Device flow OAuth initiation
  - Token polling (success, pending, expired)
  - List user repositories
  - Fetch file tree from a repo
  - Fetch raw file content
  - Error handling (rate limit, bad token, not found)
"""

import pytest
import httpx
import respx
from unittest.mock import AsyncMock, MagicMock

from app.services.github_service import GitHubService
from app.schemas.github import (
    DeviceCodeResponse,
    TokenResponse,
    GitHubRepo,
    FileTreeItem,
    FileContent,
)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def service():
    return GitHubService(client_id="test-client-id")


@pytest.fixture
def authed_service():
    svc = GitHubService(client_id="test-client-id")
    svc.set_token("gho_testtoken123")
    return svc


DEVICE_CODE_PAYLOAD = {
    "device_code": "dev_abc123",
    "user_code": "ABCD-1234",
    "verification_uri": "https://github.com/login/device",
    "expires_in": 900,
    "interval": 5,
}

TOKEN_PAYLOAD = {
    "access_token": "gho_realtoken456",
    "token_type": "bearer",
    "scope": "repo,read:user",
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
    },
    {
        "id": 2,
        "name": "secret-repo",
        "full_name": "jaiden/secret-repo",
        "private": True,
        "description": None,
        "language": "JavaScript",
        "default_branch": "main",
        "updated_at": "2025-02-01T00:00:00Z",
    },
]

FILE_TREE_PAYLOAD = {
    "tree": [
        {"path": "README.md", "type": "blob", "size": 1024, "sha": "abc"},
        {"path": "src", "type": "tree", "size": None, "sha": "def"},
        {"path": "src/main.py", "type": "blob", "size": 2048, "sha": "ghi"},
    ]
}

FILE_CONTENT_PAYLOAD = {
    "path": "src/main.py",
    "content": "cHJpbnQoJ2hlbGxvJyk=",  # base64: print('hello')
    "encoding": "base64",
    "size": 16,
    "sha": "ghi",
}


# ─────────────────────────────────────────────
# 1. Device Flow — Initiation
# ─────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_request_device_code_returns_response(service):
    """Should POST to GitHub and return a DeviceCodeResponse."""
    respx.post("https://github.com/login/device/code").mock(
        return_value=httpx.Response(200, json=DEVICE_CODE_PAYLOAD)
    )

    result = await service.request_device_code()

    assert isinstance(result, DeviceCodeResponse)
    assert result.user_code == "ABCD-1234"
    assert result.verification_uri == "https://github.com/login/device"
    assert result.interval == 5


@respx.mock
@pytest.mark.asyncio
async def test_request_device_code_includes_client_id(service):
    """Should send client_id in the request body."""
    route = respx.post("https://github.com/login/device/code").mock(
        return_value=httpx.Response(200, json=DEVICE_CODE_PAYLOAD)
    )

    await service.request_device_code()

    assert route.called
    sent_data = route.calls[0].request.content.decode()
    assert "test-client-id" in sent_data


# ─────────────────────────────────────────────
# 2. Device Flow — Token Polling
# ─────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_poll_for_token_success(service):
    """Should return TokenResponse when GitHub grants access."""
    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json=TOKEN_PAYLOAD)
    )

    result = await service.poll_for_token("dev_abc123")

    assert isinstance(result, TokenResponse)
    assert result.access_token == "gho_realtoken456"


@respx.mock
@pytest.mark.asyncio
async def test_poll_for_token_pending_returns_none(service):
    """Should return None when authorization is still pending."""
    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"error": "authorization_pending"})
    )

    result = await service.poll_for_token("dev_abc123")

    assert result is None


@respx.mock
@pytest.mark.asyncio
async def test_poll_for_token_expired_raises(service):
    """Should raise an exception when the device code has expired."""
    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"error": "expired_token"})
    )

    with pytest.raises(ValueError, match="expired"):
        await service.poll_for_token("dev_abc123")


@respx.mock
@pytest.mark.asyncio
async def test_poll_for_token_access_denied_raises(service):
    """Should raise when user explicitly denies access."""
    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"error": "access_denied"})
    )

    with pytest.raises(PermissionError):
        await service.poll_for_token("dev_abc123")


# ─────────────────────────────────────────────
# 3. Token Management
# ─────────────────────────────────────────────

def test_set_token_stores_token(service):
    """set_token should store the token for subsequent requests."""
    service.set_token("gho_mytoken")
    assert service.token == "gho_mytoken"


def test_is_authenticated_false_without_token(service):
    """Should report unauthenticated before a token is set."""
    assert service.is_authenticated() is False


def test_is_authenticated_true_with_token(authed_service):
    """Should report authenticated after set_token is called."""
    assert authed_service.is_authenticated() is True


# ─────────────────────────────────────────────
# 4. List Repositories
# ─────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_list_repos_returns_list_of_githubrepo(authed_service):
    """Should return a list of GitHubRepo objects."""
    respx.get("https://api.github.com/user/repos").mock(
        return_value=httpx.Response(200, json=REPOS_PAYLOAD)
    )

    repos = await authed_service.list_repos()

    assert len(repos) == 2
    assert all(isinstance(r, GitHubRepo) for r in repos)
    assert repos[0].name == "my-project"
    assert repos[1].private is True


@respx.mock
@pytest.mark.asyncio
async def test_list_repos_sends_auth_header(authed_service):
    """Should include Authorization header with Bearer token."""
    route = respx.get("https://api.github.com/user/repos").mock(
        return_value=httpx.Response(200, json=REPOS_PAYLOAD)
    )

    await authed_service.list_repos()

    auth_header = route.calls[0].request.headers.get("authorization")
    assert auth_header == "Bearer gho_testtoken123"


@respx.mock
@pytest.mark.asyncio
async def test_list_repos_raises_without_token(service):
    """Should raise when called without authentication."""
    with pytest.raises(PermissionError, match="authenticated"):
        await service.list_repos()


@respx.mock
@pytest.mark.asyncio
async def test_list_repos_handles_rate_limit(authed_service):
    """Should raise a specific error on GitHub rate limit response."""
    respx.get("https://api.github.com/user/repos").mock(
        return_value=httpx.Response(403, json={"message": "API rate limit exceeded"})
    )

    with pytest.raises(RuntimeError, match="rate limit"):
        await authed_service.list_repos()


# ─────────────────────────────────────────────
# 5. File Tree
# ─────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_get_file_tree_returns_list_of_items(authed_service):
    """Should return a flat list of FileTreeItem objects."""
    respx.get(
        "https://api.github.com/repos/jaiden/my-project/git/trees/main"
    ).mock(return_value=httpx.Response(200, json=FILE_TREE_PAYLOAD))

    tree = await authed_service.get_file_tree("jaiden/my-project", "main")

    assert len(tree) == 3
    assert all(isinstance(item, FileTreeItem) for item in tree)
    assert tree[0].path == "README.md"
    assert tree[0].type == "blob"
    assert tree[1].type == "tree"


@respx.mock
@pytest.mark.asyncio
async def test_get_file_tree_uses_recursive_param(authed_service):
    """Should request recursive=1 to get the full tree."""
    route = respx.get(
        "https://api.github.com/repos/jaiden/my-project/git/trees/main"
    ).mock(return_value=httpx.Response(200, json=FILE_TREE_PAYLOAD))

    await authed_service.get_file_tree("jaiden/my-project", "main")

    url = str(route.calls[0].request.url)
    assert "recursive=1" in url


@respx.mock
@pytest.mark.asyncio
async def test_get_file_tree_repo_not_found_raises(authed_service):
    """Should raise a clear error when repo doesn't exist."""
    respx.get(
        "https://api.github.com/repos/jaiden/ghost-repo/git/trees/main"
    ).mock(return_value=httpx.Response(404, json={"message": "Not Found"}))

    with pytest.raises(FileNotFoundError, match="ghost-repo"):
        await authed_service.get_file_tree("jaiden/ghost-repo", "main")


# ─────────────────────────────────────────────
# 6. File Content
# ─────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_get_file_content_returns_decoded_content(authed_service):
    """Should return FileContent with decoded (not base64) content."""
    respx.get(
        "https://api.github.com/repos/jaiden/my-project/contents/src/main.py"
    ).mock(return_value=httpx.Response(200, json=FILE_CONTENT_PAYLOAD))

    result = await authed_service.get_file_content("jaiden/my-project", "src/main.py")

    assert isinstance(result, FileContent)
    assert result.path == "src/main.py"
    assert result.content == "print('hello')"


@respx.mock
@pytest.mark.asyncio
async def test_get_file_content_file_not_found_raises(authed_service):
    """Should raise FileNotFoundError for missing files."""
    respx.get(
        "https://api.github.com/repos/jaiden/my-project/contents/missing.py"
    ).mock(return_value=httpx.Response(404, json={"message": "Not Found"}))

    with pytest.raises(FileNotFoundError, match="missing.py"):
        await authed_service.get_file_content("jaiden/my-project", "missing.py")


@respx.mock
@pytest.mark.asyncio
async def test_get_file_content_rejects_directories(authed_service):
    """Should raise ValueError when the path points to a directory."""
    respx.get(
        "https://api.github.com/repos/jaiden/my-project/contents/src"
    ).mock(return_value=httpx.Response(200, json=[
        {"name": "main.py", "type": "file"}
    ]))  # GitHub returns a list for directories

    with pytest.raises(ValueError, match="directory"):
        await authed_service.get_file_content("jaiden/my-project", "src")
