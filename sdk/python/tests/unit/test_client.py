"""AgentEval's request shapes against httpx.MockTransport: no real server, no network
socket, verifying exactly what this client sends and how it interprets a response,
the same discipline secretguard-cli's own test_cli.py uses for its login/push commands.
The server side's own business logic (auth, scoring, tenant isolation) is covered by
apps/api's real integration tests, not duplicated here.
"""

from __future__ import annotations

import json

import httpx
import pytest

from agenteval_sdk import AgentEval, AgentEvalApiError, RunTimeoutError
from agenteval_sdk.client import DatasetCase


def _client(handler) -> AgentEval:
    return AgentEval(
        api_url="http://fake-agenteval",
        api_key="aek_test_xyz",
        org_id="org-1",
        transport=httpx.MockTransport(handler),
    )


def test_every_request_carries_the_bearer_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer aek_test_xyz"
        return httpx.Response(200, json=[])

    with _client(handler) as client:
        client._request("GET", "/api/v1/orgs/org-1/agents")


def test_get_or_create_agent_reuses_an_existing_agent_by_name() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, json=[{"id": "agent-1", "name": "my-agent"}])

    with _client(handler) as client:
        agent = client.get_or_create_agent("my-agent")
    assert agent["id"] == "agent-1"


def test_get_or_create_agent_creates_when_no_match_exists() -> None:
    created: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[])
        created["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "agent-2", "name": "new-agent"})

    with _client(handler) as client:
        agent = client.get_or_create_agent("new-agent", adapter_type="http", provider="openai")
    assert agent["id"] == "agent-2"
    body = created["body"]
    assert isinstance(body, dict)
    assert body == {"name": "new-agent", "adapter_type": "http", "provider": "openai"}


def test_get_or_create_dataset_sends_every_test_case_as_the_real_payload_shape() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[])
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "ds-1", "name": "ds", "current_version_id": "v1"})

    test_case = DatasetCase(
        input={"q": "hi"},
        expected_description="say hi back",
        exact_match="hello",
        required_tool_calls=("lookup",),
    )
    with _client(handler) as client:
        client.get_or_create_dataset("ds", [test_case])
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["test_cases"][0]["input"] == {"q": "hi"}
    assert body["test_cases"][0]["expected_behavior"]["exact_match"] == "hello"
    assert body["test_cases"][0]["expected_behavior"]["required_tool_calls"] == ["lookup"]


def test_queue_run_posts_the_real_evaluation_run_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body == {
            "agent_version_id": "av-1",
            "dataset_version_id": "dv-1",
            "metric_ids": ["exact_match"],
        }
        return httpx.Response(200, json={"id": "run-1", "status": "queued"})

    with _client(handler) as client:
        run = client.queue_run("av-1", "dv-1", ["exact_match"])
    assert run["status"] == "queued"


def test_wait_for_run_polls_until_a_terminal_status() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        status = "running" if calls["n"] < 3 else "completed"
        return httpx.Response(
            200,
            json={
                "id": "run-1",
                "status": status,
                "results": []
                if status != "completed"
                else [
                    {
                        "metric_id": "exact_match",
                        "method": "deterministic",
                        "score": 1.0,
                        "passed": True,
                        "reasoning": "",
                        "same_family_warning": False,
                        "test_case_id": "case-1",
                    }
                ],
            },
        )

    with _client(handler) as client:
        result = client.wait_for_run("run-1", timeout_s=5.0, poll_s=0.01)
    assert calls["n"] == 3
    assert result.status == "completed"
    assert result.results[0].metric_id == "exact_match"


def test_wait_for_run_raises_run_timeout_error_if_never_terminal() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "run-1", "status": "running", "results": []})

    with _client(handler) as client, pytest.raises(RunTimeoutError):
        client.wait_for_run("run-1", timeout_s=0.05, poll_s=0.01)


def test_a_non_2xx_response_raises_agenteval_api_error_with_the_status_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Organization not found")

    with _client(handler) as client, pytest.raises(AgentEvalApiError) as exc_info:
        client.get_run("missing-run")
    assert exc_info.value.status_code == 404
    assert "Organization not found" in exc_info.value.body


def test_compare_sends_run_ids_and_threshold_as_query_params() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["baseline_run_id"] == "run-a"
        assert request.url.params["candidate_run_id"] == "run-b"
        assert request.url.params["regression_threshold"] == "0.1"
        return httpx.Response(
            200,
            json={
                "baseline_run_id": "run-a",
                "candidate_run_id": "run-b",
                "deltas": [
                    {
                        "metric_id": "exact_match",
                        "baseline_mean": 1.0,
                        "candidate_mean": 0.0,
                        "delta": -1.0,
                        "is_regression": True,
                    }
                ],
                "has_regression": True,
            },
        )

    with _client(handler) as client:
        result = client.compare("run-a", "run-b", regression_threshold=0.1)
    assert result.has_regression is True
    assert result.deltas[0].is_regression is True


def test_evaluate_with_an_http_url_registers_an_http_adapter_agent() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path.endswith("/agents"):
            return httpx.Response(200, json=[])
        if request.method == "POST" and path.endswith("/agents"):
            body = json.loads(request.content)
            calls.append((path, body))
            assert body["adapter_type"] == "http"
            return httpx.Response(200, json={"id": "agent-1", "name": "web-agent"})
        if request.method == "GET" and path.endswith("/versions"):
            return httpx.Response(200, json=[])
        if request.method == "POST" and path.endswith("/versions"):
            body = json.loads(request.content)
            assert body["config"] == {"endpoint_url": "http://my-agent.example/run"}
            return httpx.Response(200, json={"id": "av-1", "label": "v1"})
        if request.method == "GET" and path.endswith("/datasets"):
            return httpx.Response(200, json=[{"name": "my-dataset", "current_version_id": "dv-1"}])
        if request.method == "POST" and path.endswith("/evaluation-runs"):
            return httpx.Response(200, json={"id": "run-1", "status": "queued"})
        if "/evaluation-runs/" in path:
            return httpx.Response(
                200,
                json={
                    "id": "run-1",
                    "status": "completed",
                    "results": [],
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    with _client(handler) as client:
        result = client.evaluate(
            "http://my-agent.example/run",
            dataset="my-dataset",
            metrics=["exact_match"],
            agent_name="web-agent",
        )
    assert result.status == "completed"
    assert calls[0][1]["adapter_type"] == "http"
