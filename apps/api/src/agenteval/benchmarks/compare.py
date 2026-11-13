"""Pairwise and trend benchmark computation (docs/PLAN.md AC8, AC9). Pure functions over
already-computed per-run metric summaries, so the same comparison logic the API exposes
is also directly usable by the worker and, later, the SDK, with no database dependency
of its own; the caller is responsible for fetching the summaries from storage.
"""

from __future__ import annotations

from agenteval.evaluators.schema import BenchmarkComparison, BenchmarkDelta, RunMetricSummary

DEFAULT_REGRESSION_THRESHOLD = 0.05


def compare_runs(
    baseline_run_id: str,
    baseline: list[RunMetricSummary],
    candidate_run_id: str,
    candidate: list[RunMetricSummary],
    *,
    regression_threshold: float = DEFAULT_REGRESSION_THRESHOLD,
) -> BenchmarkComparison:
    """A delta is computed for every metric present in EITHER run (missing on one side
    is treated as absent, not zero, since a metric added or removed between versions is
    a real configuration change, not a score of 0 that would look like a false
    regression). A regression is flagged only for a metric present on both sides whose
    score dropped by more than the threshold.
    """
    baseline_by_id = {m.metric_id: m for m in baseline}
    candidate_by_id = {m.metric_id: m for m in candidate}
    metric_ids = sorted(set(baseline_by_id) | set(candidate_by_id))

    deltas = []
    for metric_id in metric_ids:
        base = baseline_by_id.get(metric_id)
        cand = candidate_by_id.get(metric_id)
        if base is None or cand is None:
            continue
        delta = cand.mean_score - base.mean_score
        deltas.append(
            BenchmarkDelta(
                metric_id=metric_id,
                baseline_mean=base.mean_score,
                candidate_mean=cand.mean_score,
                delta=delta,
                is_regression=delta < -regression_threshold,
            )
        )
    return BenchmarkComparison(
        baseline_run_id=baseline_run_id, candidate_run_id=candidate_run_id, deltas=tuple(deltas)
    )


def trend(
    run_ids_oldest_first: list[str],
    summaries_by_run: dict[str, list[RunMetricSummary]],
) -> dict[str, list[tuple[str, float]]]:
    """Every metric's mean score across a sequence of runs, oldest first, as (run_id,
    mean_score) pairs, so a dashboard can plot it as a line rather than only ever seeing
    a pairwise diff (AC9: a trend across more than two runs, not just the latest pair).
    """
    per_metric: dict[str, list[tuple[str, float]]] = {}
    for run_id in run_ids_oldest_first:
        for summary in summaries_by_run.get(run_id, []):
            per_metric.setdefault(summary.metric_id, []).append((run_id, summary.mean_score))
    return per_metric
