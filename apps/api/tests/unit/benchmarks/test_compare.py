"""Pairwise comparison and trend computation (docs/PLAN.md AC8, AC9): a metric missing
on either side is skipped, never scored as a 0 that would look like a false regression,
and a regression is flagged only when a metric present on both sides drops beyond the
threshold."""

from __future__ import annotations

from agenteval.benchmarks.compare import compare_runs, trend
from agenteval.evaluators.schema import RunMetricSummary


def _summary(metric_id: str, mean_score: float) -> RunMetricSummary:
    return RunMetricSummary(
        metric_id=metric_id, mean_score=mean_score, pass_rate=mean_score, case_count=10
    )


def test_compare_runs_computes_a_delta_per_shared_metric() -> None:
    comparison = compare_runs(
        "baseline-1",
        [_summary("task_success", 0.8), _summary("accuracy", 0.9)],
        "candidate-1",
        [_summary("task_success", 0.7), _summary("accuracy", 0.95)],
    )
    by_id = {d.metric_id: d for d in comparison.deltas}
    assert round(by_id["task_success"].delta, 10) == -0.1
    assert round(by_id["accuracy"].delta, 10) == 0.05


def test_compare_runs_flags_a_regression_beyond_the_threshold() -> None:
    comparison = compare_runs(
        "baseline-1",
        [_summary("task_success", 0.9)],
        "candidate-1",
        [_summary("task_success", 0.7)],
        regression_threshold=0.05,
    )
    assert comparison.deltas[0].is_regression is True
    assert comparison.has_regression is True


def test_compare_runs_does_not_flag_a_small_drop_within_the_threshold() -> None:
    comparison = compare_runs(
        "baseline-1",
        [_summary("task_success", 0.90)],
        "candidate-1",
        [_summary("task_success", 0.88)],
        regression_threshold=0.05,
    )
    assert comparison.deltas[0].is_regression is False
    assert comparison.has_regression is False


def test_compare_runs_does_not_flag_an_improvement_as_a_regression() -> None:
    comparison = compare_runs(
        "baseline-1",
        [_summary("task_success", 0.5)],
        "candidate-1",
        [_summary("task_success", 0.9)],
    )
    assert comparison.deltas[0].is_regression is False
    assert comparison.deltas[0].delta > 0


def test_compare_runs_skips_a_metric_present_on_only_one_side() -> None:
    """A metric added or removed between versions is a configuration change, not a
    score of 0 on the side that lacks it, which would look like a false regression."""
    comparison = compare_runs(
        "baseline-1",
        [_summary("task_success", 0.8), _summary("legacy_metric", 0.6)],
        "candidate-1",
        [_summary("task_success", 0.8), _summary("new_metric", 0.9)],
    )
    metric_ids = {d.metric_id for d in comparison.deltas}
    assert metric_ids == {"task_success"}
    assert comparison.has_regression is False


def test_trend_collects_each_metrics_mean_across_runs_oldest_first() -> None:
    summaries_by_run = {
        "run-1": [_summary("task_success", 0.6)],
        "run-2": [_summary("task_success", 0.7)],
        "run-3": [_summary("task_success", 0.9)],
    }
    result = trend(["run-1", "run-2", "run-3"], summaries_by_run)
    assert result["task_success"] == [("run-1", 0.6), ("run-2", 0.7), ("run-3", 0.9)]


def test_trend_with_a_run_missing_from_the_summaries_map_is_simply_skipped() -> None:
    result = trend(["run-1", "run-2"], {"run-1": [_summary("task_success", 0.6)]})
    assert result["task_success"] == [("run-1", 0.6)]
