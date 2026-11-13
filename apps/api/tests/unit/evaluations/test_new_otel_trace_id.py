"""A real OpenTelemetry trace id is exactly 16 bytes (32 hex characters). A prior version
of this function concatenated two uuid4 hexes and silently produced a 48-character id,
which the traces table's otel_trace_id VARCHAR(32) column only caught at insert time
against a real database; this is the fast regression test for that exact bug."""

from __future__ import annotations

from agenteval.evaluations.service import new_otel_trace_id


def test_a_new_trace_id_is_exactly_32_hex_characters() -> None:
    trace_id = new_otel_trace_id()
    assert len(trace_id) == 32
    assert all(c in "0123456789abcdef" for c in trace_id)


def test_two_calls_in_a_row_never_produce_the_same_id() -> None:
    assert new_otel_trace_id() != new_otel_trace_id()
