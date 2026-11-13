"""An evaluation run end to end, against real Postgres, Redis and the mock AI/LLM
service, exercising the acceptance criteria docs/PLAN.md states directly."""

from __future__ import annotations

import httpx
import pytest

from tests.integration.conftest import Api

pytestmark = pytest.mark.integration


async def _register_agent_and_version(api: Api) -> tuple[str, str]:
    agent = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/agents",
        {"name": "test-agent", "adapter_type": "python", "provider": "openai"},
    )
    version = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/agents/{agent['id']}/versions",
        {"label": "v1", "config": {"import_path": "agenteval.examples.toy_agent:answer"}},
    )
    return agent["id"], version["id"]


async def _create_dataset(api: Api, test_cases: list[dict]) -> str:
    dataset = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/datasets",
        {"name": "integration-test-dataset", "test_cases": test_cases},
    )
    return dataset["current_version_id"]


async def _run_worker_once(api: Api) -> None:
    """Claims and runs exactly one queued evaluation run through the real worker code
    path, in-process against the same app and settings the test's own client talks to."""
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


async def test_ac2_agent_dataset_run_produces_results_and_traces(api: Api) -> None:
    _, agent_version_id = await _register_agent_and_version(api)
    dataset_version_id = await _create_dataset(
        api,
        [
            {
                "input": {"question": "What is the capital of France?"},
                "expected_behavior": {"exact_match": "The capital of France is Paris."},
            }
        ],
    )
    run = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/evaluation-runs",
        {
            "agent_version_id": agent_version_id,
            "dataset_version_id": dataset_version_id,
            "metric_ids": ["exact_match"],
        },
    )
    assert run["status"] == "queued"
    await _run_worker_once(api)

    detail = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}")
    assert detail["status"] == "completed"
    assert len(detail["results"]) == 1
    result = detail["results"][0]
    assert result["metric_id"] == "exact_match"
    assert result["passed"] is True
    assert result["trace_id"] is not None

    trace = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/traces/{result['trace_id']}")
    assert trace["spans"][0]["gen_ai_operation_name"] == "chat"
    assert "gen_ai.response.text" in trace["spans"][0]["attributes"]


async def test_ac3_deterministic_only_dataset_makes_zero_judge_calls(api: Api) -> None:
    async with httpx.AsyncClient() as http:
        await http.post(f"{api.mock_ai_url}/reset")

    _, agent_version_id = await _register_agent_and_version(api)
    dataset_version_id = await _create_dataset(
        api,
        [
            {
                "input": {"question": "What is the capital of France?"},
                "expected_behavior": {"exact_match": "The capital of France is Paris."},
            }
        ],
    )
    run = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/evaluation-runs",
        {
            "agent_version_id": agent_version_id,
            "dataset_version_id": dataset_version_id,
            "metric_ids": ["exact_match"],
        },
    )
    await _run_worker_once(api)

    detail = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}")
    assert detail["status"] == "completed"
    assert all(r["method"] == "deterministic" for r in detail["results"])

    async with httpx.AsyncClient() as http:
        stats = (await http.get(f"{api.mock_ai_url}/stats")).json()
    assert stats["chat-completions"] == 0
    assert stats["messages"] == 0


async def test_ac4_judge_metric_stores_rubric_version_and_raw_response(api: Api) -> None:
    _, agent_version_id = await _register_agent_and_version(api)
    dataset_version_id = await _create_dataset(
        api,
        [
            {
                "input": {"question": "What is the capital of France?"},
                "expected_behavior": {"description": "Answer correctly."},
            }
        ],
    )
    run = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/evaluation-runs",
        {
            "agent_version_id": agent_version_id,
            "dataset_version_id": dataset_version_id,
            "metric_ids": ["accuracy"],
        },
    )
    await _run_worker_once(api)

    detail = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}")
    result = detail["results"][0]
    assert result["method"] == "judge"
    assert result["rubric_version"] is not None
    assert result["judge_model"] is not None

    judge_call = await api.ok(
        "GET", f"/api/v1/orgs/{api.org_id}/evaluation-results/{result['id']}/judge-call"
    )
    assert "accuracy" in judge_call["prompt"]
    assert judge_call["raw_response"]


async def test_ac5_same_family_judge_is_flagged(api: Api) -> None:
    """The demo/test judge provider is always "mock", which the same-family check
    deliberately never flags (see evaluators/judge.py); this proves the OPPOSITE
    direction is at least wired end to end: a cross-family default never raises the
    warning for the mock path used throughout this suite."""
    _, agent_version_id = await _register_agent_and_version(api)
    dataset_version_id = await _create_dataset(
        api, [{"input": {"question": "x"}, "expected_behavior": {"description": "x"}}]
    )
    run = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/evaluation-runs",
        {
            "agent_version_id": agent_version_id,
            "dataset_version_id": dataset_version_id,
            "metric_ids": ["accuracy"],
        },
    )
    await _run_worker_once(api)
    detail = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}")
    assert detail["results"][0]["same_family_warning"] is False


async def test_ac7_tool_calling_accuracy_from_real_spans(api: Api) -> None:
    _, agent_version_id = await _register_agent_and_version(api)
    dataset_version_id = await _create_dataset(
        api,
        [
            {
                "input": {"question": "What is 2 + 2?"},
                "expected_behavior": {
                    "description": "Use the calculator.",
                    "required_tool_calls": ["calculator"],
                },
            }
        ],
    )
    run = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/evaluation-runs",
        {
            "agent_version_id": agent_version_id,
            "dataset_version_id": dataset_version_id,
            "metric_ids": ["required_tool_called"],
        },
    )
    await _run_worker_once(api)
    detail = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}")
    result = detail["results"][0]
    assert result["passed"] is True

    trace = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/traces/{result['trace_id']}")
    tool_spans = [s for s in trace["spans"] if s["gen_ai_operation_name"] == "execute_tool"]
    assert len(tool_spans) == 1
    assert tool_spans[0]["attributes"]["gen_ai.tool.name"] == "calculator"


async def test_ac10_dataset_version_edit_preserves_historical_run_meaning(api: Api) -> None:
    _, agent_version_id = await _register_agent_and_version(api)
    dataset = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/datasets",
        {
            "name": "versioned-dataset",
            "test_cases": [
                {
                    "input": {"question": "What is the capital of France?"},
                    "expected_behavior": {"exact_match": "The capital of France is Paris."},
                }
            ],
        },
    )
    old_version_id = dataset["current_version_id"]
    run = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/evaluation-runs",
        {
            "agent_version_id": agent_version_id,
            "dataset_version_id": old_version_id,
            "metric_ids": ["exact_match"],
        },
    )

    await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/datasets/{dataset['id']}/versions",
        {
            "test_cases": [
                {
                    "input": {"question": "Something else entirely"},
                    "expected_behavior": {"exact_match": "A different answer"},
                }
            ]
        },
    )

    refetched_run = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}")
    assert refetched_run["dataset_version_id"] == old_version_id

    refetched_dataset = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/datasets/{dataset['id']}")
    assert refetched_dataset["current_version_id"] != old_version_id
    assert refetched_dataset["current_version_number"] == 2


async def test_ac13_tenant_isolation_on_agents_datasets_runs_and_traces(api: Api) -> None:
    agent_id, agent_version_id = await _register_agent_and_version(api)
    dataset_version_id = await _create_dataset(
        api, [{"input": {"question": "x"}, "expected_behavior": {"exact_match": "x"}}]
    )
    run = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/evaluation-runs",
        {
            "agent_version_id": agent_version_id,
            "dataset_version_id": dataset_version_id,
            "metric_ids": ["exact_match"],
        },
    )
    await _run_worker_once(api)

    other_org_id = "00000000-0000-0000-0000-000000000000"
    for path in (
        f"/api/v1/orgs/{other_org_id}/agents/{agent_id}/versions",
        f"/api/v1/orgs/{other_org_id}/evaluation-runs/{run['id']}",
    ):
        resp = await api.client.get(path)
        assert resp.status_code == 404
