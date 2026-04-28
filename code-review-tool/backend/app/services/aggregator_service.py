"""Aggregate multiple ReviewResults into a single coherent report.

Used when:
- A large file is split into N chunks and each chunk gets its own review.
- Multiple files are reviewed independently and results are merged.
"""
from app.schemas.review import ReviewResult, CodeIssue, Severity

_SEVERITY_ORDER = {
    Severity.critical: 0,
    Severity.warning: 1,
    Severity.info: 2,
}


def aggregate_results(
    results: list[ReviewResult],
    weights: list[float] | None = None,
) -> ReviewResult:
    """Merge *results* into one ReviewResult.

    Args:
        results: Individual review results to merge (must be non-empty).
        weights: Optional per-result weights for score averaging (e.g. byte
                 counts of the corresponding code sections).  Defaults to
                 equal weighting.

    Returns:
        A new :class:`ReviewResult` representing the aggregate.

    Raises:
        ValueError: If *results* is empty.
    """
    if not results:
        raise ValueError("Cannot aggregate an empty list of results.")

    if len(results) == 1:
        # Still sort issues by severity even for a single result
        r = results[0]
        sorted_issues = sorted(r.issues, key=lambda i: _SEVERITY_ORDER.get(i.severity, 99))
        if sorted_issues == r.issues:
            return r
        return ReviewResult(
            summary=r.summary,
            score=r.score,
            issues=sorted_issues,
            strengths=r.strengths,
            raw_response=r.raw_response,
        )

    if weights is None:
        weights = [1.0] * len(results)

    # Weighted average score, clamped to [0, 100]
    total_weight = sum(weights)
    raw_score = sum(r.score * w for r, w in zip(results, weights)) / total_weight
    avg_score = max(0, min(100, round(raw_score)))

    merged_issues = _merge_issues(results)
    merged_strengths = _merge_strengths(results)
    summary = _build_summary(results, avg_score)

    return ReviewResult(
        summary=summary,
        score=avg_score,
        issues=merged_issues,
        strengths=merged_strengths,
        raw_response="[aggregated from multiple reviews]",
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _merge_issues(results: list[ReviewResult]) -> list[CodeIssue]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[CodeIssue] = []

    for result in results:
        for issue in result.issues:
            # Dedup key: category + title prefix (first 50 chars, lowercased)
            key = (issue.category.value, issue.severity.value, issue.title.lower()[:50])
            if key not in seen:
                seen.add(key)
                unique.append(issue)

    return sorted(unique, key=lambda i: _SEVERITY_ORDER.get(i.severity, 99))


def _merge_strengths(results: list[ReviewResult]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for result in results:
        for s in result.strengths:
            normalised = s.lower().strip()
            if normalised not in seen:
                seen.add(normalised)
                merged.append(s)
    return merged


def _build_summary(results: list[ReviewResult], avg_score: int) -> str:
    n = len(results)
    return (
        f"Reviewed {n} file{'s' if n != 1 else ''} with an aggregate score of "
        f"{avg_score}/100. "
        + results[0].summary
    )
