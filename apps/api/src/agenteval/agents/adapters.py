"""Invoking a registered agent through its adapter type. Each adapter takes a test
case's input and returns the same AgentOutput shape the evaluators package scores,
regardless of how the agent was actually reached (docs/PLAN.md's scope section)."""

from __future__ import annotations

import importlib
from typing import Any, Protocol

import httpx

from agenteval.agents.models import Agent, AgentVersion
from agenteval.evaluators.schema import AgentOutput, ProviderFamily, ToolCall


class AdapterError(Exception):
    """The agent could not be invoked at all (a bad import path, an unreachable
    endpoint): distinct from the agent simply answering badly, which is a normal
    AgentOutput an evaluator scores, not an error."""


class AgentAdapter(Protocol):
    async def invoke(self, test_input: dict[str, Any]) -> AgentOutput: ...


class HttpAdapter:
    """Calls a registered agent's own HTTP endpoint with the test case's input as a JSON
    body, expecting back ``{"text": "...", "tool_calls": [{"name": "...", "arguments":
    {...}}, ...]}``; a tool_calls field is optional."""

    def __init__(
        self, http: httpx.AsyncClient, endpoint_url: str, provider: ProviderFamily
    ) -> None:
        self._http = http
        self._endpoint_url = endpoint_url
        self._provider = provider

    async def invoke(self, test_input: dict[str, Any]) -> AgentOutput:
        try:
            resp = await self._http.post(self._endpoint_url, json=test_input)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AdapterError(f"could not reach the agent at {self._endpoint_url}: {exc}") from exc
        tool_calls = tuple(
            ToolCall(name=t["name"], arguments=t.get("arguments", {}))
            for t in data.get("tool_calls", [])
        )
        return AgentOutput(
            text=str(data.get("text", "")), tool_calls=tool_calls, provider=self._provider
        )


class PythonAdapter:
    """Imports and calls a Python callable by its dotted path (``pkg.module:callable``),
    passing the test case's input as its only argument; the callable may be sync or
    async and must return the same dict shape HttpAdapter expects from a JSON body."""

    def __init__(self, import_path: str, provider: ProviderFamily) -> None:
        self._import_path = import_path
        self._provider = provider

    async def invoke(self, test_input: dict[str, Any]) -> AgentOutput:
        module_name, _, attr = self._import_path.partition(":")
        if not attr:
            raise AdapterError(f"import path {self._import_path!r} must be 'module:callable'")
        try:
            module = importlib.import_module(module_name)
            fn = getattr(module, attr)
        except (ImportError, AttributeError) as exc:
            raise AdapterError(f"could not import {self._import_path!r}: {exc}") from exc
        result = fn(test_input)
        if hasattr(result, "__await__"):
            result = await result
        tool_calls = tuple(
            ToolCall(name=t["name"], arguments=t.get("arguments", {}))
            for t in result.get("tool_calls", [])
        )
        return AgentOutput(
            text=str(result.get("text", "")), tool_calls=tool_calls, provider=self._provider
        )


class RecordedAdapter:
    """Scores a pre-captured trace the caller already supplied (AC2's ``recorded``
    adapter type: PLAN.md's scope section), never invoking anything live. The recorded
    output is passed in directly at construction time, one adapter instance per test
    case, since there is nothing to call."""

    def __init__(self, output: AgentOutput) -> None:
        self._output = output

    async def invoke(self, test_input: dict[str, Any]) -> AgentOutput:
        del test_input  # a recorded adapter's output never depends on the input again
        return self._output


def build_adapter(
    agent: Agent,
    version: AgentVersion,
    http: httpx.AsyncClient,
    recorded_outputs: dict[str, AgentOutput] | None = None,
    test_case_id: str | None = None,
) -> AgentAdapter:
    if agent.adapter_type == "http":
        endpoint_url = version.config.get("endpoint_url")
        if not endpoint_url:
            raise AdapterError("an http adapter's version config needs 'endpoint_url'")
        return HttpAdapter(http, str(endpoint_url), agent.provider)  # type: ignore[arg-type]
    if agent.adapter_type == "python":
        import_path = version.config.get("import_path")
        if not import_path:
            raise AdapterError("a python adapter's version config needs 'import_path'")
        return PythonAdapter(str(import_path), agent.provider)  # type: ignore[arg-type]
    if agent.adapter_type == "recorded":
        if recorded_outputs is None or test_case_id not in recorded_outputs:
            raise AdapterError(f"no recorded output supplied for test case {test_case_id}")
        return RecordedAdapter(recorded_outputs[test_case_id])
    raise AdapterError(f"unknown adapter_type: {agent.adapter_type}")
