"""
GitHubService — handles all GitHub API interactions.

Implements:
  - Device Flow OAuth (no redirect URI required, works for CLI/desktop apps)
  - Token polling with proper error states
  - Repository listing
  - File tree fetching (recursive)
  - File content fetching with base64 decoding
"""

import base64
from typing import Optional

import httpx

from app.schemas.github import (
    DeviceCodeResponse,
    TokenResponse,
    GitHubRepo,
    FileTreeItem,
    FileContent,
)

GITHUB_API = "https://api.github.com"
GITHUB_AUTH = "https://github.com"


class GitHubService:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.token: Optional[str] = None

    # ─────────────────────────────────────────
    # Auth
    # ─────────────────────────────────────────

    def set_token(self, token: str) -> None:
        """Store an OAuth access token for subsequent API calls."""
        self.token = token

    def is_authenticated(self) -> bool:
        """Return True if a token has been set."""
        return self.token is not None

    def _require_auth(self) -> None:
        if not self.is_authenticated():
            raise PermissionError(
                "Must be authenticated. Call set_token() before making API requests."
            )

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ─────────────────────────────────────────
    # Device Flow OAuth
    # ─────────────────────────────────────────

    async def request_device_code(self) -> DeviceCodeResponse:
        """
        Step 1 of GitHub Device Flow.
        Returns a user_code to display and a device_code to poll with.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_AUTH}/login/device/code",
                json={"client_id": self.client_id, "scope": "repo read:user"},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return DeviceCodeResponse(**response.json())

    async def poll_for_token(self, device_code: str) -> Optional[TokenResponse]:
        """
        Step 2 of GitHub Device Flow — poll until user authorizes or error.

        Returns:
            TokenResponse if authorized
            None if still pending (caller should retry after interval)

        Raises:
            ValueError: if the device code has expired
            PermissionError: if the user denied access
            RuntimeError: for unexpected error states
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_AUTH}/login/oauth/access_token",
                json={
                    "client_id": self.client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        # Success path
        if "access_token" in data:
            return TokenResponse(**data)

        # Error paths
        error = data.get("error", "")

        if error == "authorization_pending":
            return None  # Still waiting — caller should retry

        if error == "expired_token":
            raise ValueError("Device code has expired. Please restart the auth flow.")

        if error == "access_denied":
            raise PermissionError("User denied access to the GitHub application.")

        if error == "slow_down":
            # Caller should increase polling interval — return None to retry
            return None

        raise RuntimeError(f"Unexpected OAuth error: {error}")

    # ─────────────────────────────────────────
    # Repositories
    # ─────────────────────────────────────────

    async def list_repos(self) -> list[GitHubRepo]:
        """
        Return all repos accessible to the authenticated user,
        sorted by most recently updated.
        """
        self._require_auth()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API}/user/repos",
                headers=self._auth_headers(),
                params={"sort": "updated", "per_page": 100},
            )

        if response.status_code == 403:
            body = response.json()
            if "rate limit" in body.get("message", "").lower():
                raise RuntimeError("GitHub API rate limit exceeded. Try again later.")
            raise PermissionError(f"Access forbidden: {body.get('message')}")

        response.raise_for_status()
        return [GitHubRepo(**repo) for repo in response.json()]

    # ─────────────────────────────────────────
    # File Tree
    # ─────────────────────────────────────────

    async def get_file_tree(
        self, full_repo_name: str, branch: str = "main"
    ) -> list[FileTreeItem]:
        """
        Return the full recursive file tree for a repo branch.

        Args:
            full_repo_name: e.g. "jaiden/my-project"
            branch: branch name or commit SHA

        Returns:
            Flat list of FileTreeItem (both files and directories)
        """
        self._require_auth()

        url = f"{GITHUB_API}/repos/{full_repo_name}/git/trees/{branch}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._auth_headers(),
                params={"recursive": "1"},
            )

        if response.status_code == 404:
            raise FileNotFoundError(
                f"Repository or branch not found: {full_repo_name}@{branch}"
            )

        response.raise_for_status()
        data = response.json()

        return [
            FileTreeItem(
                path=item["path"],
                type=item["type"],
                size=item.get("size"),
                sha=item["sha"],
            )
            for item in data["tree"]
        ]

    # ─────────────────────────────────────────
    # File Content
    # ─────────────────────────────────────────

    async def get_file_content(
        self, full_repo_name: str, path: str
    ) -> FileContent:
        """
        Fetch and decode the content of a single file.

        Args:
            full_repo_name: e.g. "jaiden/my-project"
            path: file path within the repo, e.g. "src/main.py"

        Returns:
            FileContent with decoded string content

        Raises:
            FileNotFoundError: if the path doesn't exist
            ValueError: if the path points to a directory
        """
        self._require_auth()

        url = f"{GITHUB_API}/repos/{full_repo_name}/contents/{path}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._auth_headers())

        if response.status_code == 404:
            raise FileNotFoundError(f"File not found: {path}")

        response.raise_for_status()
        data = response.json()

        # GitHub returns a list when the path is a directory
        if isinstance(data, list):
            raise ValueError(
                f"Path '{path}' is a directory, not a file. "
                "Use get_file_tree() to list directory contents."
            )

        # Decode base64 content (GitHub always returns base64)
        raw = data["content"].replace("\n", "")
        decoded = base64.b64decode(raw).decode("utf-8", errors="replace")

        return FileContent(
            path=data["path"],
            content=decoded,
            encoding=data["encoding"],
            size=data["size"],
            sha=data["sha"],
        )
