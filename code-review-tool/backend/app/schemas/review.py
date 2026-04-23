from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class IssueCagetory(str, Enum):
    bug = "bug"
    complexity = "complexity"
    security = "security"
    style = "style"
    performance = "performance"


class CodeIssue(BaseModel):
    category: IssueCagetory
    severity: Severity
    line: Optional[int] = None
    title: str
    description: str
    suggestion: str


class ReviewResult(BaseModel):
    summary: str
    score: int = Field(..., ge=0, le=100, description="Overall code quality score")
    issues: list[CodeIssue]
    strengths: list[str]
    raw_response: str


class ReviewRequest(BaseModel):
    code: str
    language: Optional[str] = None
    filename: Optional[str] = None
    context: Optional[str] = None  # e.g. "This is a FastAPI route handler"


# ── Session / History ──────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    filename: Optional[str] = None
    repo: Optional[str] = None


class ReviewSession(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    filename: Optional[str]
    repo: Optional[str]
    created_at: datetime
    reviews: list["SessionReview"] = []


class SessionReview(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    code_snapshot: str
    result: ReviewResult
    created_at: datetime


class DiffLine(BaseModel):
    line_number: int
    content: str
    change_type: str  # "added" | "removed" | "unchanged"


class ReviewDiff(BaseModel):
    session_id: str
    review_a_id: str
    review_b_id: str
    lines: list[DiffLine]
    score_delta: int  # positive = improved


ReviewSession.model_rebuild()


# ── Multi-file review ──────────────────────────────────────────────────────────

class FileInput(BaseModel):
    filename: str
    code: str


class MultiFileReviewRequest(BaseModel):
    files: list[FileInput] = Field(..., min_length=1, description="At least one file required")
    context: Optional[str] = None


class FileReviewResult(BaseModel):
    filename: str
    language: str
    result: ReviewResult
    chunks_reviewed: int


class MultiFileReviewResponse(BaseModel):
    session_id: str
    review_id: str
    result: ReviewResult          # aggregated across all files
    per_file: list[FileReviewResult]
    total_chunks: int
