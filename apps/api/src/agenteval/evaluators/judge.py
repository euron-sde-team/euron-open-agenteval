"""Judge-based metrics: task success, accuracy, faithfulness, instruction adherence. Each
builds a rubric-versioned prompt and calls a judge provider, which returns a structured
score and reasoning (docs/PLAN.md's evaluation methodology).

Research into LLM-as-judge scoring (cited in docs/PLAN.md) shows asking a judge prompt to
"be fair" does nothing measurable against position, verbosity or self-preference bias;
only structural mitigations do. This module's structural mitigation is
``same_family_warning``: a judge from the same provider family as the agent under test is
flagged on every result, never silently treated as neutral (AC5). A caller (the
evaluations domain, in a later phase) is responsible for choosing a cross-family judge by
default; this module only detects and reports the condition, since it has no opinion on
which judge the caller should have picked.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from agenteval.evaluators.schema import EvaluationCase, MetricResult, ProviderFamily

# Bumped whenever a rubric's wording changes meaningfully enough that an old score under
# the same metric_id should not be compared against a new one without re-running it.
RUBRIC_VERSION = "2026-11-13.1"


class JudgeProvider(Protocol):
    """A judge call: given a rendered prompt, return (model name, raw response text).
    Implementations never see more than the rendered prompt; they have no access to the
    test case's other fields, so a prompt injection in a case's expected description
    cannot smuggle instructions past the rubric itself."""

    async def complete(self, prompt: str, *, model: str) -> tuple[str, str]: ...


@dataclass(frozen=True, slots=True)
class JudgeConfig:
    provider: ProviderFamily
    model: str


def _rubric_prompt(metric_name: str, rubric: str, case: EvaluationCase) -> str:
    tool_calls = ", ".join(t.name for t in case.actual.tool_calls) or "none"
    return (
        f"You are scoring an AI agent's response for the metric '{metric_name}'.\n\n"
        f"Rubric:\n{rubric}\n\n"
        f"Expected behavior: {case.expected.description}\n"
        f"Agent's tool calls: {tool_calls}\n"
        f"Agent's response:\n{case.actual.text}\n\n"
        'Respond with exactly one JSON object: {"score": <float 0 to 1>, "reasoning": '
        '"<one or two sentences>"}. No other text.'
    )


def _parse_judge_response(raw: str) -> tuple[float, str]:
    """A judge's response is expected to be exactly one JSON object; a judge that wraps
    it in prose (code fences, a leading sentence) still has that object extracted, since
    real providers are not perfectly obedient to a "no other text" instruction, but a
    response with no parseable object at all is a real failure, not silently scored 0."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match is None:
        raise ValueError(f"judge response had no JSON object: {raw!r}")
    parsed = json.loads(match.group(0))
    score = float(parsed["score"])
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"judge score {score} is outside [0, 1]")
    return score, str(parsed.get("reasoning", ""))


_RUBRICS: dict[str, str] = {
    "task_success": (
        "Score 1.0 if the agent fully completed the task described in 'Expected "
        "behavior'. Score 0.0 if it did not attempt the task or produced an unrelated "
        "response. Score proportionally for a partial completion."
    ),
    "accuracy": (
        "Score 1.0 if every factual claim in the agent's response is correct and "
        "consistent with the expected behavior. Score 0.0 if the response contains a "
        "clear factual error. Do not penalize style or verbosity, only correctness."
    ),
    "faithfulness": (
        "Score 1.0 if every claim in the agent's response is directly supported by the "
        "expected behavior's own context (nothing invented, nothing unsupported). Score "
        "0.0 if the agent asserted something the given context does not support."
    ),
    "instruction_adherence": (
        "Score 1.0 if the agent followed every explicit instruction in the expected "
        "behavior description (format, constraints, required steps). Score "
        "proportionally for each instruction it missed."
    ),
}


async def _run_judge_metric(
    metric_id: str,
    case: EvaluationCase,
    judge: JudgeProvider,
    judge_config: JudgeConfig,
) -> MetricResult:
    rubric = _RUBRICS[metric_id]
    prompt = _rubric_prompt(metric_id, rubric, case)
    model, raw = await judge.complete(prompt, model=judge_config.model)
    score, reasoning = _parse_judge_response(raw)
    same_family = judge_config.provider == case.actual.provider and judge_config.provider != "mock"
    return MetricResult(
        metric_id=metric_id,
        method="judge",
        score=score,
        passed=score >= 0.5,
        reasoning=reasoning,
        rubric_version=RUBRIC_VERSION,
        judge_model=model,
        judge_provider=judge_config.provider,
        raw_judge_response=raw,
        same_family_warning=same_family,
    )


JudgeMetricFn = Callable[[EvaluationCase, JudgeProvider, JudgeConfig], Awaitable[MetricResult]]


async def task_success(
    case: EvaluationCase, judge: JudgeProvider, judge_config: JudgeConfig
) -> MetricResult:
    return await _run_judge_metric("task_success", case, judge, judge_config)


async def accuracy(
    case: EvaluationCase, judge: JudgeProvider, judge_config: JudgeConfig
) -> MetricResult:
    return await _run_judge_metric("accuracy", case, judge, judge_config)


async def faithfulness(
    case: EvaluationCase, judge: JudgeProvider, judge_config: JudgeConfig
) -> MetricResult:
    return await _run_judge_metric("faithfulness", case, judge, judge_config)


async def instruction_adherence(
    case: EvaluationCase, judge: JudgeProvider, judge_config: JudgeConfig
) -> MetricResult:
    return await _run_judge_metric("instruction_adherence", case, judge, judge_config)


JUDGE_METRICS: dict[str, JudgeMetricFn] = {
    "task_success": task_success,
    "accuracy": accuracy,
    "faithfulness": faithfulness,
    "instruction_adherence": instruction_adherence,
}


async def run_judge_metrics(
    metric_ids: list[str],
    case: EvaluationCase,
    judge: JudgeProvider,
    judge_config: JudgeConfig,
) -> list[MetricResult]:
    results = []
    for metric_id in metric_ids:
        fn = JUDGE_METRICS.get(metric_id)
        if fn is None:
            raise ValueError(f"unknown judge metric: {metric_id}")
        results.append(await fn(case, judge, judge_config))
    return results
