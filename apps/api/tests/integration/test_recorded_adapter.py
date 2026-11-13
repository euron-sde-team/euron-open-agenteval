"""The ``recorded`` adapter path end to end: nothing live to invoke, so the caller (the
SDK, see sdk/python's client) pushes a trace for every test case before the worker can
score anything. Exercises the real gap this fix closed: run_evaluation's old code called
build_adapter with no recorded_outputs at all, so a recorded-adapter run always failed
with "no recorded output was supplied" the moment a worker tried it, a path no existing
integration test exercised before this file.
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import Api

pytestmark = pytest.mark.integration


async def _register_recorded_agent(api: Api) -> tuple[str, str]:
    agent = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/agents",
        {"name": "recorded-test-agent", "adapter_type": "recorded", "provider": "other"},
    )
    version = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/agents/{agent['id']}/versions",
        {"label": "v1", "config": {}},
    )
    return agent["id"], version["id"]


async def _create_dataset(api: Api, test_cases: list[dict]) -> str:
    dataset = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/datasets",
        {"name": "recorded-test-dataset", "test_cases": test_cases},
    )
    return dataset["current_version_id"]


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


async def test_a_run_for_a_recorded_agent_is_queued_as_pending_not_claimable(api: Api) -> None:
    _, agent_version_id = await _register_recorded_agent(api)
    dataset_version_id = await _create_dataset(
        api, [{"input": {"q": "hi"}, "expected_behavior": {"exact_match": "hello"}}]
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
    assert run["status"] == "pending_traces"

    from agenteval.core.container import Container
    from agenteval.evaluations.service import claim_next_run

    container: Container = api.app.state.container
    async with container.db.sessionmaker() as session:
        claimed = await claim_next_run(session, "integration-test-worker")
        # A "pending_traces" run must never be claimable: claim_next_run only selects
        # status == "queued", so the queue is empty until this run is activated.
        assert claimed is None


async def test_activating_a_run_with_no_pushed_trace_fails_cleanly_not_a_crash(api: Api) -> None:
    _, agent_version_id = await _register_recorded_agent(api)
    dataset_version_id = await _create_dataset(
        api, [{"input": {"q": "hi"}, "expected_behavior": {"exact_match": "hello"}}]
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
    await api.ok("POST", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}/activate")
    await _run_worker_once(api)

    detail = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}")
    assert detail["status"] == "failed"
    assert "no recorded output" in detail["error"]


async def test_a_pushed_trace_is_scored_and_reused_not_recorded_twice(api: Api) -> None:
    _, agent_version_id = await _register_recorded_agent(api)
    dataset_version_id = await _create_dataset(
        api,
        [
            {
                "input": {"q": "What is the capital of France?"},
                "expected_behavior": {"exact_match": "Paris"},
                "tags": [],
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
    test_cases = await api.ok(
        "GET", f"/api/v1/orgs/{api.org_id}/dataset-versions/{dataset_version_id}/test-cases"
    )
    test_case_id = test_cases[0]["id"]

    pushed_trace = await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/traces",
        {
            "otel_trace_id": "a" * 32,
            "evaluation_run_id": run["id"],
            "test_case_id": test_case_id,
            "spans": [
                {
                    "otel_span_id": "b" * 16,
                    "name": "invoke_agent",
                    "gen_ai_operation_name": "chat",
                    "started_at": "2026-01-01T12:00:00Z",
                    "ended_at": "2026-01-01T12:00:01Z",
                    "status": "ok",
                    "attributes": {
                        "gen_ai.response.text": "Paris",
                        "gen_ai.provider.name": "other",
                    },
                },
                {
                    "otel_span_id": "c" * 16,
                    "parent_otel_span_id": "b" * 16,
                    "name": "execute_tool.lookup",
                    "gen_ai_operation_name": "execute_tool",
                    "started_at": "2026-01-01T12:00:00Z",
                    "ended_at": "2026-01-01T12:00:01Z",
                    "status": "ok",
                    "attributes": {
                        "gen_ai.tool.name": "lookup",
                        "gen_ai.tool.call.arguments": {"country": "France"},
                    },
                },
            ],
        },
    )

    await api.ok("POST", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}/activate")
    await _run_worker_once(api)

    detail = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}")
    assert detail["status"] == "completed"
    assert len(detail["results"]) == 1
    result = detail["results"][0]
    assert result["metric_id"] == "exact_match"
    assert result["passed"] is True
    # The run reuses the SDK-pushed trace rather than recording a second one for the
    # same test case: exactly one trace exists for this run and test case.
    assert result["trace_id"] == pushed_trace["id"]

    trace = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/traces/{result['trace_id']}")
    assert len(trace["spans"]) == 2
    tool_span = next(s for s in trace["spans"] if s["gen_ai_operation_name"] == "execute_tool")
    assert tool_span["attributes"]["gen_ai.tool.name"] == "lookup"


async def test_tool_calling_is_scored_from_the_pushed_trace_not_reparsed_text(api: Api) -> None:
    _, agent_version_id = await _register_recorded_agent(api)
    dataset_version_id = await _create_dataset(
        api,
        [
            {
                "input": {"q": "look something up"},
                "expected_behavior": {"required_tool_calls": ["lookup"]},
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
    test_cases = await api.ok(
        "GET", f"/api/v1/orgs/{api.org_id}/dataset-versions/{dataset_version_id}/test-cases"
    )
    test_case_id = test_cases[0]["id"]

    await api.ok(
        "POST",
        f"/api/v1/orgs/{api.org_id}/traces",
        {
            "otel_trace_id": "d" * 32,
            "evaluation_run_id": run["id"],
            "test_case_id": test_case_id,
            "spans": [
                {
                    "otel_span_id": "e" * 16,
                    "name": "invoke_agent",
                    "gen_ai_operation_name": "chat",
                    "started_at": "2026-01-01T12:00:00Z",
                    "ended_at": "2026-01-01T12:00:01Z",
                    "status": "ok",
                    "attributes": {
                        "gen_ai.response.text": "I looked it up for you",
                        "gen_ai.provider.name": "other",
                    },
                },
                {
                    "otel_span_id": "f" * 16,
                    "parent_otel_span_id": "e" * 16,
                    "name": "execute_tool.lookup",
                    "gen_ai_operation_name": "execute_tool",
                    "started_at": "2026-01-01T12:00:00Z",
                    "ended_at": "2026-01-01T12:00:01Z",
                    "status": "ok",
                    "attributes": {"gen_ai.tool.name": "lookup", "gen_ai.tool.call.arguments": {}},
                },
            ],
        },
    )
    await api.ok("POST", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}/activate")
    await _run_worker_once(api)

    detail = await api.ok("GET", f"/api/v1/orgs/{api.org_id}/evaluation-runs/{run['id']}")
    assert detail["status"] == "completed"
    result = detail["results"][0]
    assert result["metric_id"] == "required_tool_called"
    assert result["passed"] is True
