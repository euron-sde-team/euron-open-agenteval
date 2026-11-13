"""Benchmark comparison and trend between real evaluation runs (AC8, AC9)."""

from __future__ import annotations

import uuid

import pytest

from tests.integration.conftest import Api

pytestmark = pytest.mark.integration


async def _run_worker_once(api: Api) -> None:
    from agenteval.core.container import Container
    from agenteval.evaluations.models import EvaluationRun
    from agenteval.evaluations.service import claim_next_run, run_evaluation

    container: Container = api.app.state.container
    async with container.db.sessionmaker() as session:
        run = await claim_next_run(session, "integration-test-worker")
        assert run is not None, "expected a queued run"
        await session.commit()
        run_id = run.id
    async with container.db.sessionmaker() as session:
        run = await session.get(EvaluationRun, run_id)
        assert run is not None
        await run_evaluation(session, container.settings, container.http, run)


async def _queue_and_run(api: Api, import_path: str, dataset_version_id: str) -> str:
    agent = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/agents",
        {
            "name": f"bench-agent-{uuid.uuid4().hex[:8]}",
            "adapter_type": "python",
            "provider": "openai",
        },
    )
    version = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/agents/{agent['id']}/versions",
        {"label": "v1", "config": {"import_path": import_path}},
    )
    run = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/evaluation-runs",
        {
            "agent_version_id": version["id"],
            "dataset_version_id": dataset_version_id,
            "metric_ids": ["exact_match"],
        },
    )
    await _run_worker_once(api)
    return run["id"]


async def test_ac8_benchmark_comparison_flags_a_real_regression(api: Api) -> None:
    dataset = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/datasets",
        {
            "name": "bench-dataset",
            "test_cases": [
                {
                    "input": {"question": "What is the capital of France?"},
                    "expected_behavior": {"exact_match": "The capital of France is Paris."},
                }
            ],
        },
    )
    dataset_version_id = dataset["current_version_id"]

    baseline_run_id = await _queue_and_run(
        api, "agenteval.examples.toy_agent:answer", dataset_version_id
    )
    # The demo seed's own v2 agent hedges on this exact question (see
    # demo/support_agent.py's module docstring), genuinely failing exact_match where
    # the toy agent passes: a real regression, not a staged one.
    candidate_run_id = await _queue_and_run(
        api, "agenteval.demo.support_agent:answer_v2", dataset_version_id
    )

    comparison = await api.ok(
        "GET",
        f"/api/v1/orgs/{api.org_id}/benchmarks/compare"
        f"?baseline_run_id={baseline_run_id}&candidate_run_id={candidate_run_id}",
    )
    deltas_by_metric = {d["metric_id"]: d for d in comparison["deltas"]}
    assert deltas_by_metric["exact_match"]["is_regression"] is True
    assert comparison["has_regression"] is True


async def test_ac9_trend_across_more_than_two_runs(api: Api) -> None:
    dataset = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/datasets",
        {
            "name": "trend-dataset",
            "test_cases": [
                {
                    "input": {"question": "What is the capital of France?"},
                    "expected_behavior": {"exact_match": "The capital of France is Paris."},
                }
            ],
        },
    )
    dataset_version_id = dataset["current_version_id"]

    run_ids = [
        await _queue_and_run(api, "agenteval.examples.toy_agent:answer", dataset_version_id)
        for _ in range(3)
    ]

    query = "&".join(f"run_ids={r}" for r in run_ids)
    trend = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/benchmarks/trend?{query}")
    points = trend["series"]["exact_match"]
    assert len(points) == 3
    assert [p["run_id"] for p in points] == run_ids
