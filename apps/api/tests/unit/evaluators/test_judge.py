"""Judge-based metrics against the deterministic MockJudgeProvider: every metric records
its rubric version and raw judge response (AC4), and the cross-family self-preference
warning fires exactly when it should (AC5)."""

from __future__ import annotations

import pytest

from agenteval.evaluators.judge import (
    RUBRIC_VERSION,
    JudgeConfig,
    JudgeMetricFn,
    accuracy,
    faithfulness,
    instruction_adherence,
    run_judge_metrics,
    task_success,
)
from agenteval.evaluators.mock_judge import MockJudgeProvider, score_for_text
from agenteval.evaluators.schema import (
    AgentOutput,
    EvaluationCase,
    ExpectedBehavior,
    ProviderFamily,
)


def _case(text: str, provider: ProviderFamily = "other") -> EvaluationCase:
    return EvaluationCase(
        test_case_id="tc-1",
        expected=ExpectedBehavior(description="Answer the question correctly."),
        actual=AgentOutput(text=text, provider=provider),
    )


@pytest.mark.parametrize("metric_fn", [task_success, accuracy, faithfulness, instruction_adherence])
async def test_every_judge_metric_records_rubric_version_and_raw_response(
    metric_fn: JudgeMetricFn,
) -> None:
    judge = MockJudgeProvider()
    case = _case("a flawless answer")
    result = await metric_fn(case, judge, JudgeConfig(provider="openai", model="mock-model"))
    assert result.method == "judge"
    assert result.rubric_version == RUBRIC_VERSION
    assert result.judge_model == "mock-model"
    assert result.raw_judge_response is not None
    assert result.score == 1.0
    assert result.passed is True


async def test_a_wrong_answer_scores_low_and_fails() -> None:
    judge = MockJudgeProvider()
    case = _case("this is wrong")
    result = await task_success(case, judge, JudgeConfig(provider="openai", model="mock-model"))
    assert result.score == 0.0
    assert result.passed is False


async def test_rescoring_the_same_case_with_the_mock_judge_is_deterministic() -> None:
    judge = MockJudgeProvider()
    case = _case("partially correct")
    first = await accuracy(case, judge, JudgeConfig(provider="openai", model="mock-model"))
    second = await accuracy(case, judge, JudgeConfig(provider="openai", model="mock-model"))
    assert first.score == second.score == 0.5


async def test_same_family_warning_fires_when_judge_and_agent_share_a_provider() -> None:
    judge = MockJudgeProvider()
    case = _case("a perfect answer", provider="openai")
    result = await task_success(case, judge, JudgeConfig(provider="openai", model="mock-model"))
    assert result.same_family_warning is True


async def test_same_family_warning_does_not_fire_across_different_providers() -> None:
    judge = MockJudgeProvider()
    case = _case("a perfect answer", provider="anthropic")
    result = await task_success(case, judge, JudgeConfig(provider="openai", model="mock-model"))
    assert result.same_family_warning is False


async def test_same_family_warning_never_fires_for_the_mock_provider() -> None:
    """The mock provider is used by every unit test and the demo; it would otherwise
    warn on every single result, defeating the warning's purpose of flagging a real
    deployment's real same-family misconfiguration."""
    judge = MockJudgeProvider()
    case = _case("a perfect answer", provider="mock")
    result = await task_success(case, judge, JudgeConfig(provider="mock", model="mock-model"))
    assert result.same_family_warning is False


async def test_run_judge_metrics_runs_every_requested_metric() -> None:
    judge = MockJudgeProvider()
    case = _case("a good enough answer")
    results = await run_judge_metrics(
        ["task_success", "accuracy"], case, judge, JudgeConfig(provider="openai", model="m")
    )
    assert {r.metric_id for r in results} == {"task_success", "accuracy"}
    assert judge.call_count == 2


async def test_run_judge_metrics_rejects_an_unknown_metric_id() -> None:
    judge = MockJudgeProvider()
    with pytest.raises(ValueError, match="unknown judge metric"):
        await run_judge_metrics(
            ["not_a_real_metric"], _case("x"), judge, JudgeConfig("openai", "m")
        )


def test_score_for_text_matches_every_documented_keyword() -> None:
    assert score_for_text("this is flawless") == 1.0
    assert score_for_text("PERFECT work") == 1.0
    assert score_for_text("good enough for now") == 0.8
    assert score_for_text("partially done") == 0.5
    assert score_for_text("this is wrong") == 0.0
    assert score_for_text("the agent fails here") == 0.0
    assert score_for_text("no keyword present") == 0.9
