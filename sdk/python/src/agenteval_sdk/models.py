"""Lightweight read-only views over the server's own JSON responses. These are not the
server's real dataclasses/ORM models (those live in apps/api and are not importable by a
remote caller who only has an API key), just typed wrappers around the response bodies
`AgentEval.evaluate()` and `AgentEval.compare()` already fetched over HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MetricResultView:
    metric_id: str
    method: str
    score: float
    passed: bool
    reasoning: str
    same_family_warning: bool
    test_case_id: str


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """The outcome of one `AgentEval.evaluate()` call: a completed run's id and every
    per-test-case, per-metric result. `summary()` never collapses these into one
    composite number (docs/PLAN.md's AC12), it reports each metric's mean separately."""

    run_id: str
    status: str
    results: tuple[MetricResultView, ...] = field(default_factory=tuple)

    def mean_scores(self) -> dict[str, float]:
        totals: dict[str, list[float]] = {}
        for r in self.results:
            totals.setdefault(r.metric_id, []).append(r.score)
        return {metric_id: sum(scores) / len(scores) for metric_id, scores in totals.items()}

    def summary(self) -> str:
        if not self.results:
            return f"run {self.run_id}: {self.status}, no results yet"
        lines = [f"run {self.run_id}: {self.status}"]
        for metric_id, mean in sorted(self.mean_scores().items()):
            lines.append(f"  {metric_id}: {mean:.2f}")
        warned = {r.metric_id for r in self.results if r.same_family_warning}
        if warned:
            lines.append(f"  warning: same-family judge used for {', '.join(sorted(warned))}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class BenchmarkDeltaView:
    metric_id: str
    baseline_mean: float
    candidate_mean: float
    delta: float
    is_regression: bool


@dataclass(frozen=True, slots=True)
class BenchmarkComparisonResult:
    baseline_run_id: str
    candidate_run_id: str
    deltas: tuple[BenchmarkDeltaView, ...]
    has_regression: bool

    def summary(self) -> str:
        lines = [f"{self.baseline_run_id} -> {self.candidate_run_id}"]
        for d in sorted(self.deltas, key=lambda d: d.metric_id):
            flag = " REGRESSION" if d.is_regression else ""
            lines.append(f"  {d.metric_id}: {d.baseline_mean:.2f} -> {d.candidate_mean:.2f}{flag}")
        return "\n".join(lines)


def metric_result_from_json(data: dict[str, Any]) -> MetricResultView:
    return MetricResultView(
        metric_id=data["metric_id"],
        method=data["method"],
        score=data["score"],
        passed=data["passed"],
        reasoning=data.get("reasoning", ""),
        same_family_warning=data.get("same_family_warning", False),
        test_case_id=data["test_case_id"],
    )


def benchmark_delta_from_json(data: dict[str, Any]) -> BenchmarkDeltaView:
    return BenchmarkDeltaView(
        metric_id=data["metric_id"],
        baseline_mean=data["baseline_mean"],
        candidate_mean=data["candidate_mean"],
        delta=data["delta"],
        is_regression=data["is_regression"],
    )
