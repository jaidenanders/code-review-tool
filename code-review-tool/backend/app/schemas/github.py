from pydantic import BaseModel
from typing import Optional


class DeviceCodeRequest(BaseModel):
    client_id: str


class DeviceCodeResponse(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    scope: str


class GitHubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    description: Optional[str] = None
    language: Optional[str] = None
    default_branch: str
    updated_at: str


class FileTreeItem(BaseModel):
    path: str
    type: str  # "blob" (file) or "tree" (directory)
    size: Optional[int] = None
    sha: str


class FileContent(BaseModel):
    path: str
    content: str
    encoding: str
    size: int
    sha: str
