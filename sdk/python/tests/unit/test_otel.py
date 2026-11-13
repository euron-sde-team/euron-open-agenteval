"""build_invocation_spans/new_otel_trace_id: the SDK's own copy of the same OpenTelemetry
GenAI attribute mapping apps/api's evaluations.service.build_invocation_spans uses, for a
local Python callable this SDK invokes itself. Mirrors that function's own unit tests
(apps/api/tests/unit/evaluations/test_build_invocation_spans.py) to prove the two stay
byte-identical in shape."""

from __future__ import annotations

from datetime import UTC, datetime

from agenteval_sdk.otel import AgentOutputIn, ToolCallIn, build_invocation_spans, new_otel_trace_id

_STARTED = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_ENDED = datetime(2026, 1, 1, 12, 0, 1, tzinfo=UTC)


def test_an_output_with_no_tool_calls_produces_exactly_one_chat_span() -> None:
    output = AgentOutputIn(text="hello", provider="openai")
    spans = build_invocation_spans(output, _STARTED, _ENDED)
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "invoke_agent"
    assert span.gen_ai_operation_name == "chat"
    assert span.parent_otel_span_id is None
    assert span.attributes["gen_ai.response.text"] == "hello"
    assert span.attributes["gen_ai.provider.name"] == "openai"


def test_the_chat_span_gets_a_real_16_char_otel_span_id() -> None:
    output = AgentOutputIn(text="hello")
    span = build_invocation_spans(output, _STARTED, _ENDED)[0]
    assert len(span.otel_span_id) == 16
    assert all(c in "0123456789abcdef" for c in span.otel_span_id)


def test_one_tool_call_produces_a_second_execute_tool_span_parented_to_the_chat_span() -> None:
    output = AgentOutputIn(
        text="used a tool",
        tool_calls=(ToolCallIn(name="calculator", arguments={"expression": "2 + 2"}),),
    )
    spans = build_invocation_spans(output, _STARTED, _ENDED)
    assert len(spans) == 2
    chat_span, tool_span = spans
    assert tool_span.name == "execute_tool.calculator"
    assert tool_span.gen_ai_operation_name == "execute_tool"
    assert tool_span.parent_otel_span_id == chat_span.otel_span_id
    assert tool_span.attributes["gen_ai.tool.name"] == "calculator"
    assert tool_span.attributes["gen_ai.tool.call.arguments"] == {"expression": "2 + 2"}


def test_to_payload_sends_isoformat_timestamps_and_omits_parent_when_none() -> None:
    output = AgentOutputIn(text="hello")
    span = build_invocation_spans(output, _STARTED, _ENDED)[0]
    payload = span.to_payload()
    assert payload["started_at"] == _STARTED.isoformat()
    assert payload["ended_at"] == _ENDED.isoformat()
    assert "parent_otel_span_id" not in payload


def test_to_payload_includes_parent_when_set() -> None:
    output = AgentOutputIn(text="x", tool_calls=(ToolCallIn(name="t", arguments={}),))
    spans = build_invocation_spans(output, _STARTED, _ENDED)
    tool_payload = spans[1].to_payload()
    assert tool_payload["parent_otel_span_id"] == spans[0].otel_span_id


def test_new_otel_trace_id_is_32_hex_characters() -> None:
    trace_id = new_otel_trace_id()
    assert len(trace_id) == 32
    assert all(c in "0123456789abcdef" for c in trace_id)


def test_two_calls_in_a_row_never_reuse_the_same_trace_id() -> None:
    assert new_otel_trace_id() != new_otel_trace_id()
