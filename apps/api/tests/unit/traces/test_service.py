"""Pure logic in the traces domain: extracting a tool call from a span's gen_ai.*
attributes (AC7's "score from real spans, not re-parsed free text"), with no database.
Span is a plain, unflushed model instance here, the same as _extract_tool_call itself
only ever reads already-loaded attributes.
"""

from __future__ import annotations

import uuid

from agenteval.traces.models import Span
from agenteval.traces.service import _extract_tool_call


def _span(attributes: dict[str, object]) -> Span:
    return Span(
        trace_id=uuid.uuid4(),
        otel_span_id="abcdef0123456789",
        name="execute_tool.calculator",
        attributes=attributes,
    )


def test_a_span_with_a_tool_name_produces_a_tool_call_record() -> None:
    span = _span({"gen_ai.tool.name": "calculator", "gen_ai.tool.call.arguments": {"x": 1}})
    span.id = uuid.uuid4()
    record = _extract_tool_call(span)
    assert record is not None
    assert record.tool_name == "calculator"
    assert record.arguments == {"x": 1}
    assert record.span_id == span.id


def test_a_span_with_no_tool_name_produces_nothing() -> None:
    """A plain chat span (no gen_ai.tool.name attribute at all) is not a tool call, and
    must not produce a spurious ToolCallRecord."""
    span = _span({"gen_ai.response.text": "hello"})
    assert _extract_tool_call(span) is None


def test_a_tool_call_records_its_result_and_error_when_present() -> None:
    span = _span(
        {
            "gen_ai.tool.name": "search",
            "gen_ai.tool.call.arguments": {"query": "weather"},
            "gen_ai.tool.call.result": {"forecast": "sunny"},
            "error.message": None,
        }
    )
    span.id = uuid.uuid4()
    record = _extract_tool_call(span)
    assert record is not None
    assert record.result == {"forecast": "sunny"}


def test_a_tool_name_that_is_an_empty_string_is_treated_as_no_tool_call() -> None:
    span = _span({"gen_ai.tool.name": ""})
    assert _extract_tool_call(span) is None
