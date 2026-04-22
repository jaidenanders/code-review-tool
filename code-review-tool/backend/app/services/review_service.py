"""
ReviewService — orchestrates the full review pipeline.

Responsibilities:
  - Call OllamaService with structured prompt
  - Parse the raw text response into a ReviewResult
  - Handle malformed/partial model output gracefully
"""

import re
from typing import Optional

from app.services.ollama_service import OllamaService
from app.schemas.review import (
    ReviewResult,
    CodeIssue,
    Severity,
    IssueCagetory,
)

# Maps model output strings to enums (case-insensitive)
_CATEGORY_MAP = {
    "bug": IssueCagetory.bug,
    "complexity": IssueCagetory.complexity,
    "security": IssueCagetory.security,
    "style": IssueCagetory.style,
    "performance": IssueCagetory.performance,
}

_SEVERITY_MAP = {
    "critical": Severity.critical,
    "warning": Severity.warning,
    "info": Severity.info,
}


class ReviewService:
    def __init__(self, ollama: OllamaService):
        self.ollama = ollama

    # ─────────────────────────────────────────
    # Orchestration
    # ─────────────────────────────────────────

    async def review(
        self,
        code: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
    ) -> ReviewResult:
        """
        Full pipeline: send code to Ollama, parse response, return ReviewResult.
        Raises RuntimeError / ValueError from OllamaService unchanged.
        """
        raw = await self.ollama.review_code(
            code=code,
            language=language,
            context=context,
        )
        return self.parse_response(raw)

    # ─────────────────────────────────────────
    # Parsing
    # ─────────────────────────────────────────

    def parse_response(self, raw: str) -> ReviewResult:
        """
        Parse a structured Ollama response into a ReviewResult.

        Expected format:
            SUMMARY: <text>
            SCORE: <int>
            ISSUES:
            - <category> | <severity> | line <N|?> | <title> | <description> | <suggestion>
            STRENGTHS:
            - <text>
            END
        """
        summary = self._extract_summary(raw)
        score = self._extract_score(raw)
        issues = self._extract_issues(raw)
        strengths = self._extract_strengths(raw)

        return ReviewResult(
            summary=summary,
            score=score,
            issues=issues,
            strengths=strengths,
            raw_response=raw,
        )

    def _extract_summary(self, raw: str) -> str:
        match = re.search(r"SUMMARY:\s*(.+?)(?=\n\s*\n|\nSCORE:|\nISSUES:)", raw, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_score(self, raw: str) -> int:
        match = re.search(r"SCORE:\s*(\d+)", raw)
        if not match:
            return 50  # neutral default when model omits score
        score = int(match.group(1))
        return max(0, min(100, score))  # clamp to [0, 100]

    def _extract_issues(self, raw: str) -> list[CodeIssue]:
        # Find the ISSUES block — everything between "ISSUES:" and "STRENGTHS:" or "END"
        issues_block = re.search(
            r"ISSUES:\s*\n(.*?)(?=\nSTRENGTHS:|\nEND)", raw, re.DOTALL
        )
        if not issues_block:
            return []

        issues: list[CodeIssue] = []
        for line in issues_block.group(1).splitlines():
            line = line.strip().lstrip("- ").strip()
            if not line:
                continue
            issue = self._parse_issue_line(line)
            if issue:
                issues.append(issue)
        return issues

    def _parse_issue_line(self, line: str) -> Optional[CodeIssue]:
        """
        Parse a pipe-delimited issue line:
          <category> | <severity> | line <N|?> | <title> | <description> | <suggestion>
        Returns None if the line is malformed.
        """
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 6:
            return None

        category_str = parts[0].lower()
        severity_str = parts[1].lower()

        category = _CATEGORY_MAP.get(category_str)
        severity = _SEVERITY_MAP.get(severity_str)

        if not category or not severity:
            return None

        # Parse line number: "line 4" → 4, "line ?" → None
        line_part = parts[2].strip().lower()
        line_match = re.search(r"line\s+(\d+|\?)", line_part)
        line_number: Optional[int] = None
        if line_match and line_match.group(1) != "?":
            line_number = int(line_match.group(1))

        return CodeIssue(
            category=category,
            severity=severity,
            line=line_number,
            title=parts[3].strip(),
            description=parts[4].strip(),
            suggestion=parts[5].strip(),
        )

    def _extract_strengths(self, raw: str) -> list[str]:
        strengths_block = re.search(
            r"STRENGTHS:\s*\n(.*?)(?=\nEND|\Z)", raw, re.DOTALL
        )
        if not strengths_block:
            return []

        strengths = []
        for line in strengths_block.group(1).splitlines():
            line = line.strip().lstrip("- ").strip()
            if line:
                strengths.append(line)
        return strengths
