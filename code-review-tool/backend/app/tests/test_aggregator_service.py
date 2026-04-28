"""TDD tests for AggregatorService — merging multiple ReviewResults."""
import pytest
from app.services.aggregator_service import aggregate_results
from app.schemas.review import ReviewResult, CodeIssue, Severity, IssueCagetory


def make_result(score: int, issues: list[CodeIssue] | None = None, strengths: list[str] | None = None) -> ReviewResult:
    return ReviewResult(
        summary=f"Summary for score {score}",
        score=score,
        issues=issues or [],
        strengths=strengths or [],
        raw_response="raw",
    )


def make_issue(
    title: str = "Issue",
    severity: Severity = Severity.warning,
    category: IssueCagetory = IssueCagetory.style,
    line: int | None = None,
) -> CodeIssue:
    return CodeIssue(
        category=category,
        severity=severity,
        line=line,
        title=title,
        description="desc",
        suggestion="suggestion",
    )


class TestAggregateResults:
    def test_single_result_returned_unchanged(self):
        r = make_result(75)
        result = aggregate_results([r])
        assert result.score == 75

    def test_two_results_averages_score(self):
        r1 = make_result(60)
        r2 = make_result(80)
        result = aggregate_results([r1, r2])
        assert result.score == 70

    def test_three_results_averages_score(self):
        results = [make_result(s) for s in [50, 70, 90]]
        result = aggregate_results(results)
        assert result.score == 70

    def test_score_clamped_to_100(self):
        result = aggregate_results([make_result(100), make_result(100)])
        assert result.score == 100

    def test_score_clamped_to_0(self):
        result = aggregate_results([make_result(0), make_result(0)])
        assert result.score == 0

    def test_weighted_average_score(self):
        r1 = make_result(100)
        r2 = make_result(0)
        # weight r1 = 3x, r2 = 1x → (300 + 0) / 4 = 75
        result = aggregate_results([r1, r2], weights=[3.0, 1.0])
        assert result.score == 75

    def test_issues_are_merged(self):
        r1 = make_result(70, issues=[make_issue("Issue A")])
        r2 = make_result(80, issues=[make_issue("Issue B")])
        result = aggregate_results([r1, r2])
        titles = {i.title for i in result.issues}
        assert "Issue A" in titles
        assert "Issue B" in titles

    def test_duplicate_issues_are_deduplicated(self):
        issue = make_issue("Null pointer dereference", category=IssueCagetory.bug)
        r1 = make_result(70, issues=[issue])
        r2 = make_result(80, issues=[issue])
        result = aggregate_results([r1, r2])
        assert len(result.issues) == 1

    def test_issues_sorted_critical_first(self):
        issues = [
            make_issue("Info thing", severity=Severity.info),
            make_issue("Critical bug", severity=Severity.critical),
            make_issue("Warning", severity=Severity.warning),
        ]
        r = make_result(70, issues=issues)
        result = aggregate_results([r])
        assert result.issues[0].severity == Severity.critical
        assert result.issues[1].severity == Severity.warning
        assert result.issues[2].severity == Severity.info

    def test_strengths_are_merged(self):
        r1 = make_result(70, strengths=["Good naming"])
        r2 = make_result(80, strengths=["Clear structure"])
        result = aggregate_results([r1, r2])
        assert "Good naming" in result.strengths
        assert "Clear structure" in result.strengths

    def test_duplicate_strengths_are_deduplicated(self):
        r1 = make_result(70, strengths=["Good naming", "Clear docs"])
        r2 = make_result(80, strengths=["Good naming", "Good tests"])
        result = aggregate_results([r1, r2])
        assert result.strengths.count("Good naming") == 1

    def test_summary_mentions_file_count(self):
        results = [make_result(70), make_result(80), make_result(90)]
        result = aggregate_results(results)
        assert "3" in result.summary

    def test_empty_list_raises(self):
        with pytest.raises((ValueError, IndexError)):
            aggregate_results([])

    def test_different_category_same_title_not_deduplicated(self):
        i1 = make_issue("Naming", category=IssueCagetory.style)
        i2 = make_issue("Naming", category=IssueCagetory.bug)
        r = make_result(70, issues=[i1, i2])
        result = aggregate_results([r])
        assert len(result.issues) == 2

    def test_raw_response_marked_as_aggregated(self):
        result = aggregate_results([make_result(70), make_result(80)])
        assert "aggregat" in result.raw_response.lower()
