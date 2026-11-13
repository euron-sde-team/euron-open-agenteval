"""build_adapter's dispatch logic: choosing an HttpAdapter, PythonAdapter or
RecordedAdapter by the agent's adapter_type, and refusing cleanly when a version's
config is missing what that adapter type needs. No database: Agent and AgentVersion are
plain, unflushed model instances here, exactly as build_adapter itself only ever reads
their already-loaded attributes."""

from __future__ import annotations

import httpx
import pytest

from agenteval.agents.adapters import (
    AdapterError,
    HttpAdapter,
    PythonAdapter,
    RecordedAdapter,
    build_adapter,
)
from agenteval.agents.models import Agent, AgentVersion
from agenteval.evaluators.schema import AgentOutput


def _agent(adapter_type: str, provider: str = "openai") -> Agent:
    return Agent(organization_id=None, name="x", adapter_type=adapter_type, provider=provider)


def _version(config: dict[str, object]) -> AgentVersion:
    return AgentVersion(agent_id=None, label="v1", config=config)


def test_http_adapter_type_builds_an_http_adapter() -> None:
    http = httpx.AsyncClient()
    adapter = build_adapter(_agent("http"), _version({"endpoint_url": "http://x/invoke"}), http)
    assert isinstance(adapter, HttpAdapter)


def test_http_adapter_without_an_endpoint_url_raises_adapter_error() -> None:
    http = httpx.AsyncClient()
    with pytest.raises(AdapterError, match="endpoint_url"):
        build_adapter(_agent("http"), _version({}), http)


def test_python_adapter_type_builds_a_python_adapter() -> None:
    http = httpx.AsyncClient()
    adapter = build_adapter(_agent("python"), _version({"import_path": "os.path:join"}), http)
    assert isinstance(adapter, PythonAdapter)


def test_python_adapter_without_an_import_path_raises_adapter_error() -> None:
    http = httpx.AsyncClient()
    with pytest.raises(AdapterError, match="import_path"):
        build_adapter(_agent("python"), _version({}), http)


def test_recorded_adapter_type_builds_a_recorded_adapter_when_output_is_supplied() -> None:
    http = httpx.AsyncClient()
    output = AgentOutput(text="canned answer")
    adapter = build_adapter(
        _agent("recorded"),
        _version({}),
        http,
        recorded_outputs={"case-1": output},
        test_case_id="case-1",
    )
    assert isinstance(adapter, RecordedAdapter)


def test_recorded_adapter_with_no_matching_output_raises_adapter_error() -> None:
    http = httpx.AsyncClient()
    with pytest.raises(AdapterError, match="no recorded output"):
        build_adapter(
            _agent("recorded"), _version({}), http, recorded_outputs={}, test_case_id="case-1"
        )


def test_an_unknown_adapter_type_raises_adapter_error() -> None:
    http = httpx.AsyncClient()
    with pytest.raises(AdapterError, match="unknown adapter_type"):
        build_adapter(_agent("not-a-real-type"), _version({}), http)


async def test_python_adapter_invokes_the_real_imported_callable() -> None:
    """A real import path pointing at a function in this test module itself, run
    through the actual PythonAdapter.invoke, not mocked."""
    adapter = PythonAdapter("tests.unit.agents.test_adapters:_toy_answer", "openai")
    output = await adapter.invoke({"question": "ping"})
    assert output.text == "pong"
    assert output.provider == "openai"


async def test_python_adapter_with_a_bad_import_path_raises_adapter_error() -> None:
    adapter = PythonAdapter("not.a.real.module:fn", "openai")
    with pytest.raises(AdapterError, match="could not import"):
        await adapter.invoke({})


async def test_python_adapter_import_path_without_a_colon_raises_adapter_error() -> None:
    adapter = PythonAdapter("os.path.join", "openai")
    with pytest.raises(AdapterError, match="module:callable"):
        await adapter.invoke({})


async def test_recorded_adapter_returns_the_supplied_output_regardless_of_input() -> None:
    output = AgentOutput(text="always this")
    adapter = RecordedAdapter(output)
    result = await adapter.invoke({"question": "anything"})
    assert result is output


def _toy_answer(test_input: dict[str, object]) -> dict[str, object]:
    del test_input
    return {"text": "pong"}
