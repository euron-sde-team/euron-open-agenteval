"""Builds the same OpenTelemetry GenAI-shaped span list the server's worker produces
(agenteval.evaluations.service.build_invocation_spans), for a local Python callable the
SDK invokes itself rather than asking a registered agent's worker to invoke it. Mirrors
that function's attribute names exactly (never a bespoke schema), so a trace recorded by
the SDK and a trace recorded by the worker look identical once stored (docs/PLAN.md's
"Trace format" section).

This module has no dependency on the real OpenTelemetry SDK's exporter machinery: it
builds plain dicts matching the server's SpanIn shape directly, since the server is the
one real destination for these spans (POST /api/v1/orgs/{org_id}/traces), not a generic
OTel collector. opentelemetry-api is still a project dependency so a caller's own
instrumentation (if they already use OTel) composes with this without a second SDK.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ToolCallIn:
    name: str
    arguments: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentOutputIn:
    text: str
    tool_calls: tuple[ToolCallIn, ...] = ()
    provider: str = "other"


@dataclass(frozen=True, slots=True)
class SpanDict:
    otel_span_id: str
    name: str
    gen_ai_operation_name: str
    started_at: datetime
    ended_at: datetime
    status: str
    attributes: dict[str, object]
    parent_otel_span_id: str | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "otel_span_id": self.otel_span_id,
            "name": self.name,
            "gen_ai_operation_name": self.gen_ai_operation_name,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "status": self.status,
            "attributes": self.attributes,
        }
        if self.parent_otel_span_id is not None:
            payload["parent_otel_span_id"] = self.parent_otel_span_id
        return payload


def new_otel_trace_id() -> str:
    """A real 32-hex-char (16-byte) OpenTelemetry trace id, matching
    agenteval.evaluations.service.new_otel_trace_id exactly."""
    return uuid.uuid4().hex


def build_invocation_spans(
    output: AgentOutputIn, started_at: datetime, ended_at: datetime
) -> list[SpanDict]:
    """One invoke_agent span plus one execute_tool child span per tool call, using the
    real gen_ai.* attribute namespace. Pure and network-free, directly unit-testable."""
    agent_span_id = uuid.uuid4().hex[:16]
    spans = [
        SpanDict(
            otel_span_id=agent_span_id,
            name="invoke_agent",
            gen_ai_operation_name="chat",
            started_at=started_at,
            ended_at=ended_at,
            status="ok",
            attributes={
                "gen_ai.response.text": output.text,
                "gen_ai.provider.name": output.provider,
            },
        )
    ]
    for tool_call in output.tool_calls:
        spans.append(
            SpanDict(
                otel_span_id=uuid.uuid4().hex[:16],
                parent_otel_span_id=agent_span_id,
                name=f"execute_tool.{tool_call.name}",
                gen_ai_operation_name="execute_tool",
                started_at=started_at,
                ended_at=ended_at,
                status="ok",
                attributes={
                    "gen_ai.tool.name": tool_call.name,
                    "gen_ai.tool.call.arguments": tool_call.arguments,
                },
            )
        )
    return spans
