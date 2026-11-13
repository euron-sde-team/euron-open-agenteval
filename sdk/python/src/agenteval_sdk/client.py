"""The AgentEval client: register an agent, create a dataset, queue and wait for an
evaluation run, and compare runs, against a real running AgentEval server. Every method
calls a real endpoint the dashboard and the worker themselves use (see apps/api's
agents/, datasets/, evaluations/ and benchmarks/ routers); this client never
reimplements scoring, the server always does the real evaluation.
"""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self

import httpx

from agenteval_sdk.errors import AgentEvalApiError, RunTimeoutError
from agenteval_sdk.models import (
    BenchmarkComparisonResult,
    EvaluationResult,
    benchmark_delta_from_json,
    metric_result_from_json,
)
from agenteval_sdk.otel import AgentOutputIn, ToolCallIn, build_invocation_spans, new_otel_trace_id

_TERMINAL_STATUSES = frozenset({"completed", "failed"})


@dataclass(frozen=True, slots=True)
class DatasetCase:
    """One dataset test case, matching apps/api's datasets.schemas.TestCaseIn shape."""

    input: dict[str, Any]
    expected_description: str = ""
    exact_match: str | None = None
    regex: str | None = None
    json_schema: dict[str, Any] | None = None
    required_tool_calls: tuple[str, ...] = ()
    forbidden_tool_calls: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "input": self.input,
            "expected_behavior": {
                "description": self.expected_description,
                "exact_match": self.exact_match,
                "regex": self.regex,
                "json_schema": self.json_schema,
                "required_tool_calls": list(self.required_tool_calls),
                "forbidden_tool_calls": list(self.forbidden_tool_calls),
            },
            "tags": list(self.tags),
        }


# A caller may pass a dotted "module:callable" or "http://..." string (the agent is
# already registered this way, or a worker can reach it), or a live Python callable the
# SDK itself invokes locally (scored as a "recorded" adapter run, since nothing server
# side can import a live object from this process).
AgentRef = str | Callable[[dict[str, Any]], Any]


class AgentEval:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        org_id: str,
        *,
        timeout_s: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """``transport`` is for tests only: httpx's own MockTransport or ASGITransport,
        so a unit test can verify this client's request shapes against a fake or an
        in-process real app with no real server process and no network socket, the
        same seam apps/api's own tests use against mockllm."""
        self._org_id = org_id
        self._http = httpx.Client(
            base_url=api_url.rstrip("/"),
            headers={"authorization": f"Bearer {api_key}"},
            timeout=timeout_s,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- low level -----------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._http.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise AgentEvalApiError(resp.status_code, resp.text)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # -- agents ----------------------------------------------------------------------

    def get_or_create_agent(
        self, name: str, adapter_type: str = "recorded", provider: str = "other"
    ) -> dict[str, Any]:
        agents = self._request("GET", f"/api/v1/orgs/{self._org_id}/agents")
        for agent in agents:
            if agent["name"] == name:
                return agent  # type: ignore[no-any-return]
        return self._request(  # type: ignore[no-any-return]
            "POST",
            f"/api/v1/orgs/{self._org_id}/agents",
            json={"name": name, "adapter_type": adapter_type, "provider": provider},
        )

    def get_or_create_agent_version(
        self, agent_id: str, label: str, config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        versions = self._request("GET", f"/api/v1/orgs/{self._org_id}/agents/{agent_id}/versions")
        for version in versions:
            if version["label"] == label:
                return version  # type: ignore[no-any-return]
        return self._request(  # type: ignore[no-any-return]
            "POST",
            f"/api/v1/orgs/{self._org_id}/agents/{agent_id}/versions",
            json={"label": label, "config": config or {}},
        )

    # -- datasets ----------------------------------------------------------------------

    def get_or_create_dataset(self, name: str, test_cases: list[DatasetCase]) -> dict[str, Any]:
        datasets = self._request("GET", f"/api/v1/orgs/{self._org_id}/datasets")
        for dataset in datasets:
            if dataset["name"] == name:
                return dataset  # type: ignore[no-any-return]
        return self._request(  # type: ignore[no-any-return]
            "POST",
            f"/api/v1/orgs/{self._org_id}/datasets",
            json={"name": name, "test_cases": [tc.to_payload() for tc in test_cases]},
        )

    def create_dataset_version(
        self, dataset_id: str, test_cases: list[DatasetCase]
    ) -> dict[str, Any]:
        """Replaces a dataset's test cases, creating a NEW version (AC10): a past
        evaluation run keeps its original dataset_version_id, so this never changes
        what an already-completed run's score means."""
        return self._request(  # type: ignore[no-any-return]
            "POST",
            f"/api/v1/orgs/{self._org_id}/datasets/{dataset_id}/versions",
            json={"test_cases": [tc.to_payload() for tc in test_cases]},
        )

    # -- evaluation runs -----------------------------------------------------------

    def queue_run(
        self, agent_version_id: str, dataset_version_id: str, metric_ids: list[str]
    ) -> dict[str, Any]:
        return self._request(  # type: ignore[no-any-return]
            "POST",
            f"/api/v1/orgs/{self._org_id}/evaluation-runs",
            json={
                "agent_version_id": agent_version_id,
                "dataset_version_id": dataset_version_id,
                "metric_ids": metric_ids,
            },
        )

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._request(  # type: ignore[no-any-return]
            "GET", f"/api/v1/orgs/{self._org_id}/evaluation-runs/{run_id}"
        )

    def activate_run(self, run_id: str) -> dict[str, Any]:
        """A ``recorded`` adapter run is queued as "pending_traces", not "queued", so a
        worker's claim query never races the traces this SDK is still pushing; call
        this once every test case's trace has been pushed, to make it claimable."""
        return self._request(  # type: ignore[no-any-return]
            "POST", f"/api/v1/orgs/{self._org_id}/evaluation-runs/{run_id}/activate"
        )

    def wait_for_run(
        self, run_id: str, *, timeout_s: float = 120.0, poll_s: float = 1.0
    ) -> EvaluationResult:
        """Polls GET .../evaluation-runs/{run_id} until it reaches a terminal status.
        A run only progresses once a worker process claims it (see apps/api's
        worker.py); this SDK never claims or runs anything itself for a registered
        http/python agent, it only waits for the server's own worker to."""
        deadline = time.monotonic() + timeout_s
        while True:
            data = self.get_run(run_id)
            if data["status"] in _TERMINAL_STATUSES:
                results = tuple(metric_result_from_json(r) for r in data.get("results", []))
                return EvaluationResult(run_id=run_id, status=data["status"], results=results)
            if time.monotonic() >= deadline:
                raise RunTimeoutError(run_id, timeout_s)
            time.sleep(poll_s)

    # -- the brief's proposed shape --------------------------------------------------

    def evaluate(
        self,
        agent: AgentRef,
        dataset: str | list[DatasetCase],
        metrics: list[str],
        *,
        agent_name: str | None = None,
        agent_version_label: str | None = None,
        provider: str = "other",
        timeout_s: float = 120.0,
    ) -> EvaluationResult:
        """`evaluator.evaluate(agent=..., dataset=..., metrics=[...])`, the shape
        docs/PLAN.md's SDK section specifies. ``agent`` is one of:

        - an ``http://`` or ``https://`` URL: registers (or reuses) an ``http`` adapter
          agent pointed at that endpoint; a worker invokes it for real.
        - a ``"module:callable"`` import path: registers (or reuses) a ``python``
          adapter agent; a worker imports and calls it for real, in the worker's own
          environment (the path must be importable there, not just in this process).
        - a live Python callable: invoked **locally, in this process**, once per test
          case, and the resulting output is pushed to the server as a ``recorded``
          adapter run with a real OpenTelemetry trace (see agenteval_sdk.otel), since a
          live object cannot be handed to a remote worker to import.

        ``dataset`` is either an existing dataset's name, or a list of ``DatasetCase`` to
        create (or add as a new version of) a dataset named after the agent.
        """
        if callable(agent) and not isinstance(agent, str):
            resolved_name = agent_name or str(getattr(agent, "__name__", "local-agent"))
            return self._evaluate_local_callable(
                agent,
                dataset,
                metrics,
                agent_name=resolved_name,
                agent_version_label=agent_version_label or "local",
                provider=provider,
                timeout_s=timeout_s,
            )

        assert isinstance(agent, str)
        adapter_type = "http" if agent.startswith(("http://", "https://")) else "python"
        config = {"endpoint_url": agent} if adapter_type == "http" else {"import_path": agent}
        agent_row = self.get_or_create_agent(
            agent_name or agent, adapter_type=adapter_type, provider=provider
        )
        version_row = self.get_or_create_agent_version(
            agent_row["id"], agent_version_label or "v1", config
        )
        dataset_version_id = self._resolve_dataset_version(agent_row["name"], dataset)
        run = self.queue_run(version_row["id"], dataset_version_id, metrics)
        return self.wait_for_run(run["id"], timeout_s=timeout_s)

    def _resolve_dataset_version(self, default_name: str, dataset: str | list[DatasetCase]) -> str:
        if isinstance(dataset, str):
            datasets = self._request("GET", f"/api/v1/orgs/{self._org_id}/datasets")
            for row in datasets:
                if row["name"] == dataset:
                    return str(row["current_version_id"])
            raise AgentEvalApiError(404, f"no dataset named {dataset!r}")
        dataset_row = self.get_or_create_dataset(default_name, dataset)
        return str(dataset_row["current_version_id"])

    def _evaluate_local_callable(
        self,
        agent: Callable[[dict[str, Any]], Any],
        dataset: str | list[DatasetCase],
        metrics: list[str],
        *,
        agent_name: str,
        agent_version_label: str,
        provider: str,
        timeout_s: float,
    ) -> EvaluationResult:
        agent_row = self.get_or_create_agent(agent_name, adapter_type="recorded", provider=provider)
        version_row = self.get_or_create_agent_version(agent_row["id"], agent_version_label)
        dataset_version_id = self._resolve_dataset_version(agent_name, dataset)
        # Queued as "pending_traces" (apps/api's queue_run, since this agent's adapter
        # type is "recorded"): a worker cannot claim it until activate_run is called
        # below, so the traces pushed in between can never race a worker's claim.
        run = self.queue_run(version_row["id"], dataset_version_id, metrics)
        self._run_local_callable_and_push_traces(agent, run["id"])
        self.activate_run(run["id"])
        return self.wait_for_run(run["id"], timeout_s=timeout_s)

    def _run_local_callable_and_push_traces(
        self, agent: Callable[[dict[str, Any]], Any], run_id: str
    ) -> None:
        """For a ``recorded`` adapter, the worker expects the caller to have already
        supplied every test case's output as a trace before it claims the run; this
        invokes the live callable once per test case in the run's dataset version and
        pushes a real OpenTelemetry trace for each, exactly the shape
        evaluations.service.build_invocation_spans produces server side."""
        run = self.get_run(run_id)
        dataset_version_id = run["dataset_version_id"]
        test_cases = self._request(
            "GET",
            f"/api/v1/orgs/{self._org_id}/dataset-versions/{dataset_version_id}/test-cases",
        )
        for case in test_cases:
            started_at = datetime.now(UTC)
            raw = agent(case["input"])
            if inspect.isawaitable(raw):
                raise TypeError(
                    "AgentEval.evaluate() calls a local callable synchronously; pass a "
                    "sync function, or an http:// endpoint / module:callable path for "
                    "an async agent the worker invokes instead"
                )
            ended_at = datetime.now(UTC)
            output = AgentOutputIn(
                text=str(raw.get("text", "")),
                tool_calls=tuple(
                    ToolCallIn(name=t["name"], arguments=t.get("arguments", {}))
                    for t in raw.get("tool_calls", [])
                ),
                provider="other",
            )
            spans = build_invocation_spans(output, started_at, ended_at)
            self._request(
                "POST",
                f"/api/v1/orgs/{self._org_id}/traces",
                json={
                    "otel_trace_id": new_otel_trace_id(),
                    "evaluation_run_id": run_id,
                    "test_case_id": case["id"],
                    "spans": [s.to_payload() for s in spans],
                },
            )

    # -- benchmarks ------------------------------------------------------------------

    def compare(
        self, baseline_run_id: str, candidate_run_id: str, *, regression_threshold: float = 0.05
    ) -> BenchmarkComparisonResult:
        data = self._request(
            "GET",
            f"/api/v1/orgs/{self._org_id}/benchmarks/compare",
            params={
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": candidate_run_id,
                "regression_threshold": regression_threshold,
            },
        )
        deltas = tuple(benchmark_delta_from_json(d) for d in data["deltas"])
        return BenchmarkComparisonResult(
            baseline_run_id=data["baseline_run_id"],
            candidate_run_id=data["candidate_run_id"],
            deltas=deltas,
            has_regression=data["has_regression"],
        )

    def trend(self, run_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        data = self._request(
            "GET",
            f"/api/v1/orgs/{self._org_id}/benchmarks/trend",
            params=[("run_ids", r) for r in run_ids],
        )
        return data["series"]  # type: ignore[no-any-return]
