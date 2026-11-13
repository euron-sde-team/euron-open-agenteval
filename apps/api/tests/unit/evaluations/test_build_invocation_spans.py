"""build_invocation_spans: the pure OpenTelemetry GenAI attribute mapping from one
agent invocation's output to the span shape the traces domain stores (docs/PLAN.md's
trace format section, AC6/AC7). No database: this is exactly the function the worker
calls before any ingestion happens."""

from __future__ import annotations

from datetime import UTC, datetime

from agenteval.evaluations.service import build_invocation_spans
from agenteval.evaluators.schema import AgentOutput, ToolCall

_STARTED = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_ENDED = datetime(2026, 1, 1, 12, 0, 1, tzinfo=UTC)


def test_an_output_with_no_tool_calls_produces_exactly_one_chat_span() -> None:
    output = AgentOutput(text="hello", provider="openai")
    spans = build_invocation_spans(output, _STARTED, _ENDED)
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "invoke_agent"
    assert span.gen_ai_operation_name == "chat"
    assert span.parent_otel_span_id is None
    assert span.attributes["gen_ai.response.text"] == "hello"
    assert span.attributes["gen_ai.provider.name"] == "openai"
    assert span.started_at == _STARTED
    assert span.ended_at == _ENDED
    assert span.status == "ok"


def test_the_chat_span_gets_a_real_16_char_otel_span_id() -> None:
    output = AgentOutput(text="hello")
    span = build_invocation_spans(output, _STARTED, _ENDED)[0]
    assert len(span.otel_span_id) == 16
    assert all(c in "0123456789abcdef" for c in span.otel_span_id)


def test_one_tool_call_produces_a_second_execute_tool_span_parented_to_the_chat_span() -> None:
    output = AgentOutput(
        text="used a tool",
        tool_calls=(ToolCall(name="calculator", arguments={"expression": "2 + 2"}),),
    )
    spans = build_invocation_spans(output, _STARTED, _ENDED)
    assert len(spans) == 2
    chat_span, tool_span = spans
    assert tool_span.name == "execute_tool.calculator"
    assert tool_span.gen_ai_operation_name == "execute_tool"
    assert tool_span.parent_otel_span_id == chat_span.otel_span_id
    assert tool_span.attributes["gen_ai.tool.name"] == "calculator"
    assert tool_span.attributes["gen_ai.tool.call.arguments"] == {"expression": "2 + 2"}


def test_multiple_tool_calls_each_produce_their_own_span_with_a_distinct_id() -> None:
    output = AgentOutput(
        text="used two tools",
        tool_calls=(
            ToolCall(name="calculator", arguments={"expression": "2 + 2"}),
            ToolCall(name="search", arguments={"query": "weather"}),
        ),
    )
    spans = build_invocation_spans(output, _STARTED, _ENDED)
    assert len(spans) == 3
    tool_spans = spans[1:]
    assert {s.name for s in tool_spans} == {"execute_tool.calculator", "execute_tool.search"}
    assert tool_spans[0].otel_span_id != tool_spans[1].otel_span_id
    assert all(s.parent_otel_span_id == spans[0].otel_span_id for s in tool_spans)


def test_two_calls_in_a_row_never_reuse_the_same_span_id() -> None:
    """uuid4-based ids: a collision would be a real bug worth catching, not just
    theoretically impossible."""
    output = AgentOutput(text="x")
    first = build_invocation_spans(output, _STARTED, _ENDED)[0]
    second = build_invocation_spans(output, _STARTED, _ENDED)[0]
    assert first.otel_span_id != second.otel_span_id
