"""EvaluationResult/BenchmarkComparisonResult: pure view objects, no network. The one
thing worth proving here is docs/PLAN.md's AC12: summary() never collapses every metric
into one bare composite number, it always reports each metric's mean separately."""

from __future__ import annotations

from agenteval_sdk.models import (
    BenchmarkComparisonResult,
    EvaluationResult,
    MetricResultView,
    benchmark_delta_from_json,
    metric_result_from_json,
)


def _result(metric_id: str, score: float, same_family_warning: bool = False) -> MetricResultView:
    return MetricResultView(
        metric_id=metric_id,
        method="judge",
        score=score,
        passed=score >= 0.5,
        reasoning="",
        same_family_warning=same_family_warning,
        test_case_id="case-1",
    )


def test_mean_scores_averages_per_metric_across_test_cases() -> None:
    result = EvaluationResult(
        run_id="run-1",
        status="completed",
        results=(_result("accuracy", 1.0), _result("accuracy", 0.0)),
    )
    assert result.mean_scores() == {"accuracy": 0.5}


def test_summary_reports_every_metric_separately_not_one_composite() -> None:
    result = EvaluationResult(
        run_id="run-1",
        status="completed",
        results=(_result("accuracy", 0.9), _result("task_success", 0.4)),
    )
    summary = result.summary()
    assert "accuracy: 0.90" in summary
    assert "task_success: 0.40" in summary
    # AC12: no single number that collapses the two metrics into one score.
    assert "0.65" not in summary


def test_summary_with_no_results_says_so_without_crashing() -> None:
    result = EvaluationResult(run_id="run-1", status="running", results=())
    assert "no results yet" in result.summary()


def test_summary_surfaces_a_same_family_judge_warning() -> None:
    result = EvaluationResult(
        run_id="run-1",
        status="completed",
        results=(_result("accuracy", 0.9, same_family_warning=True),),
    )
    assert "warning" in result.summary()
    assert "accuracy" in result.summary()


def test_metric_result_from_json_round_trips_the_real_server_shape() -> None:
    data = {
        "metric_id": "exact_match",
        "method": "deterministic",
        "score": 1.0,
        "passed": True,
        "reasoning": "",
        "same_family_warning": False,
        "test_case_id": "case-1",
    }
    view = metric_result_from_json(data)
    assert view.metric_id == "exact_match"
    assert view.passed is True


def test_benchmark_comparison_summary_flags_a_regression() -> None:
    comparison = BenchmarkComparisonResult(
        baseline_run_id="run-a",
        candidate_run_id="run-b",
        deltas=(
            benchmark_delta_from_json(
                {
                    "metric_id": "exact_match",
                    "baseline_mean": 1.0,
                    "candidate_mean": 0.0,
                    "delta": -1.0,
                    "is_regression": True,
                }
            ),
        ),
        has_regression=True,
    )
    summary = comparison.summary()
    assert "REGRESSION" in summary
    assert "run-a -> run-b" in summary
