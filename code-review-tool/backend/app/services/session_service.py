"""
SessionService — persists review sessions and generates code diffs.

Backed by SQLAlchemy async (SQLite for dev, PostgreSQL for production).
"""

import json
import uuid
import difflib
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import SessionModel, ReviewModel
from app.schemas.review import (
    ReviewResult,
    ReviewSession,
    SessionReview,
    ReviewDiff,
    DiffLine,
    CodeIssue,
)


def _new_id() -> str:
    return str(uuid.uuid4())


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─────────────────────────────────────────
    # Sessions
    # ─────────────────────────────────────────

    async def create_session(
        self,
        filename: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> str:
        """Create a new review session and return its ID."""
        session = SessionModel(
            id=_new_id(),
            filename=filename,
            repo=repo,
        )
        self.db.add(session)
        await self.db.commit()
        return session.id

    async def get_session(self, session_id: str) -> Optional[ReviewSession]:
        """Return a ReviewSession with all its reviews, or None if not found."""
        result = await self.db.execute(
            select(SessionModel)
            .where(SessionModel.id == session_id)
            .options(selectinload(SessionModel.reviews))
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_schema(row)

    async def list_sessions(self) -> list[ReviewSession]:
        """Return all sessions ordered newest first (no reviews loaded)."""
        result = await self.db.execute(
            select(SessionModel).order_by(SessionModel.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._to_schema(r, include_reviews=False) for r in rows]

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and its reviews. No-op if not found."""
        await self.db.execute(
            delete(ReviewModel).where(ReviewModel.session_id == session_id)
        )
        await self.db.execute(
            delete(SessionModel).where(SessionModel.id == session_id)
        )
        await self.db.commit()

    # ─────────────────────────────────────────
    # Reviews
    # ─────────────────────────────────────────

    async def save_review(
        self,
        session_id: str,
        code: str,
        result: ReviewResult,
    ) -> str:
        """
        Persist a ReviewResult under a session. Returns the new review ID.
        Raises ValueError if the session doesn't exist.
        """
        # Verify session exists
        exists = await self.db.execute(
            select(SessionModel.id).where(SessionModel.id == session_id)
        )
        if exists.scalar_one_or_none() is None:
            raise ValueError(f"Session not found: {session_id}")

        review = ReviewModel(
            id=_new_id(),
            session_id=session_id,
            code_snapshot=code,
            summary=result.summary,
            score=result.score,
            issues_json=json.dumps([i.model_dump() for i in result.issues]),
            strengths_json=json.dumps(result.strengths),
            raw_response=result.raw_response,
        )
        self.db.add(review)
        await self.db.commit()
        return review.id

    async def _get_review_model(self, review_id: str) -> Optional[ReviewModel]:
        result = await self.db.execute(
            select(ReviewModel).where(ReviewModel.id == review_id)
        )
        return result.scalar_one_or_none()

    # ─────────────────────────────────────────
    # Diff
    # ─────────────────────────────────────────

    async def get_diff(
        self,
        session_id: str,
        review_a_id: str,
        review_b_id: str,
    ) -> ReviewDiff:
        """
        Generate a line-level diff between two code snapshots.

        Raises:
            ValueError: if either review ID is not found
        """
        rev_a = await self._get_review_model(review_a_id)
        rev_b = await self._get_review_model(review_b_id)

        if rev_a is None or rev_b is None:
            missing = review_a_id if rev_a is None else review_b_id
            raise ValueError(f"Review not found: {missing}")

        lines_a = rev_a.code_snapshot.splitlines()
        lines_b = rev_b.code_snapshot.splitlines()

        diff_lines: list[DiffLine] = []
        line_num = 0

        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, lines_a, lines_b
        ).get_opcodes():
            if tag == "equal":
                for content in lines_a[i1:i2]:
                    line_num += 1
                    diff_lines.append(
                        DiffLine(line_number=line_num, content=content, change_type="unchanged")
                    )
            elif tag in ("replace", "delete"):
                for content in lines_a[i1:i2]:
                    line_num += 1
                    diff_lines.append(
                        DiffLine(line_number=line_num, content=content, change_type="removed")
                    )
                if tag == "replace":
                    for content in lines_b[j1:j2]:
                        line_num += 1
                        diff_lines.append(
                            DiffLine(line_number=line_num, content=content, change_type="added")
                        )
            elif tag == "insert":
                for content in lines_b[j1:j2]:
                    line_num += 1
                    diff_lines.append(
                        DiffLine(line_number=line_num, content=content, change_type="added")
                    )

        return ReviewDiff(
            session_id=session_id,
            review_a_id=review_a_id,
            review_b_id=review_b_id,
            lines=diff_lines,
            score_delta=rev_b.score - rev_a.score,
        )

    # ─────────────────────────────────────────
    # Schema conversion helpers
    # ─────────────────────────────────────────

    def _review_to_schema(self, r: ReviewModel) -> SessionReview:
        issues_data = json.loads(r.issues_json)
        strengths = json.loads(r.strengths_json)

        result = ReviewResult(
            summary=r.summary,
            score=r.score,
            issues=[CodeIssue(**i) for i in issues_data],
            strengths=strengths,
            raw_response=r.raw_response,
        )
        return SessionReview(
            id=r.id,
            session_id=r.session_id,
            code_snapshot=r.code_snapshot,
            result=result,
            created_at=r.created_at,
        )

    def _to_schema(
        self, row: SessionModel, include_reviews: bool = True
    ) -> ReviewSession:
        reviews = (
            [self._review_to_schema(r) for r in row.reviews]
            if include_reviews and row.reviews is not None
            else []
        )
        return ReviewSession(
            id=row.id,
            filename=row.filename,
            repo=row.repo,
            created_at=row.created_at,
            reviews=reviews,
        )
