"""The shared shapes every evaluator (deterministic or judge-based) produces and
consumes. Imported directly by the API, the worker and the SDK, so a dataset evaluated
locally by the SDK and a run executed by the worker apply byte-identical scoring logic
(see docs/PLAN.md's architecture section)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# A metric's result is a number in [0, 1]; deterministic checks report exactly 0.0 or
# 1.0 (pass/fail), judge-based metrics report a continuous score, both on the same scale
# so a benchmark comparison can treat every metric uniformly regardless of its method.
MetricMethod = Literal["deterministic", "judge"]
ProviderFamily = Literal["openai", "anthropic", "mock", "other"]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """One tool invocation an agent made during a run, as recorded in its trace. Tool
    accuracy metrics score against this, never by re-parsing the agent's free-text
    output (see docs/PLAN.md's AC7)."""

    name: str
    arguments: dict[str, object]


@dataclass(frozen=True, slots=True)
class AgentOutput:
    """What an agent produced for one test case: its final text output plus every tool
    call it made along the way, exactly what a deterministic check or a judge prompt
    scores against."""

    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    provider: ProviderFamily = "other"


@dataclass(frozen=True, slots=True)
class ExpectedBehavior:
    """A test case's expectations, matching the brief's example shape: an expected
    outcome description a judge-based metric is scored against, an exact-match or regex
    target a deterministic check is scored against, and required/forbidden tool calls."""

    description: str = ""
    exact_match: str | None = None
    regex: str | None = None
    json_schema: dict[str, object] | None = None
    required_tool_calls: tuple[str, ...] = ()
    forbidden_tool_calls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MetricResult:
    """One metric's result for one test case. ``rubric_version`` and ``raw_judge_response``
    are ``None`` for a deterministic check (there is no judge, nothing to version or
    store); both are always populated for a judge-based metric, so a score can be
    audited, not just trusted (AC4)."""

    metric_id: str
    method: MetricMethod
    score: float  # in [0, 1]
    passed: bool
    reasoning: str = ""
    rubric_version: str | None = None
    judge_model: str | None = None
    judge_provider: ProviderFamily | None = None
    raw_judge_response: str | None = None
    same_family_warning: bool = False


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """One test case's worth of input needed to score it: what the agent produced, and
    what was expected."""

    test_case_id: str
    expected: ExpectedBehavior
    actual: AgentOutput


@dataclass(frozen=True, slots=True)
class RunMetricSummary:
    """A metric's aggregate across every test case in one evaluation run, the unit a
    benchmark comparison's per-metric delta is computed from (AC8)."""

    metric_id: str
    mean_score: float
    pass_rate: float
    case_count: int


@dataclass(frozen=True, slots=True)
class BenchmarkDelta:
    """One metric's comparison between a baseline run and a candidate run."""

    metric_id: str
    baseline_mean: float
    candidate_mean: float
    delta: float  # candidate - baseline; negative means the candidate did worse
    is_regression: bool


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    baseline_run_id: str
    candidate_run_id: str
    deltas: tuple[BenchmarkDelta, ...] = field(default_factory=tuple)

    @property
    def has_regression(self) -> bool:
        return any(d.is_regression for d in self.deltas)
