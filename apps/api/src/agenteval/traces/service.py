"""Trace ingestion and query. A trace is identified by its real OpenTelemetry trace id,
never an AgentEval-invented one, so any OTel-compatible exporter's trace lands here with
no translation. Every span's gen_ai.* attributes are stored verbatim; a tool-call span
(gen_ai_operation_name == "execute_tool") is additionally extracted into its own
ToolCallRecord row, so the tool_inspector can score tool accuracy by querying that table
directly rather than re-parsing attributes (AC7, docs/PLAN.md's traces domain note)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.errors import NotFoundError
from agenteval.evaluators.schema import ToolCall
from agenteval.traces.models import Span, ToolCallRecord, Trace
from agenteval.traces.schemas import SpanIn, SpanOut, TraceOut


def _span_out(span: Span) -> SpanOut:
    return SpanOut(
        id=span.id,
        otel_span_id=span.otel_span_id,
        parent_otel_span_id=span.parent_otel_span_id,
        name=span.name,
        gen_ai_operation_name=span.gen_ai_operation_name,
        started_at=span.started_at,
        ended_at=span.ended_at,
        status=span.status,
        attributes=span.attributes,
    )


async def _trace_out(session: AsyncSession, trace: Trace) -> TraceOut:
    spans = await session.scalars(
        select(Span).where(Span.trace_id == trace.id).order_by(Span.started_at)
    )
    return TraceOut(
        id=trace.id,
        organization_id=trace.organization_id,
        otel_trace_id=trace.otel_trace_id,
        evaluation_run_id=trace.evaluation_run_id,
        test_case_id=trace.test_case_id,
        spans=[_span_out(s) for s in spans],
        created_at=trace.created_at,
    )


def _extract_tool_call(span: Span) -> ToolCallRecord | None:
    """gen_ai.tool.name / gen_ai.tool.call.arguments / gen_ai.tool.call.result per the
    OpenTelemetry GenAI semantic conventions; a span with no tool name is not a tool-call
    span at all (an LLM chat span, say), and contributes no ToolCallRecord."""
    tool_name = span.attributes.get("gen_ai.tool.name")
    if not tool_name:
        return None
    return ToolCallRecord(
        span_id=span.id,
        tool_name=str(tool_name),
        arguments=span.attributes.get("gen_ai.tool.call.arguments", {}),
        result=span.attributes.get("gen_ai.tool.call.result"),
        error=span.attributes.get("error.message"),
    )


async def ingest_trace(
    session: AsyncSession,
    organization_id: uuid.UUID,
    otel_trace_id: str,
    spans_in: list[SpanIn],
    evaluation_run_id: uuid.UUID | None = None,
    test_case_id: uuid.UUID | None = None,
) -> TraceOut:
    """Idempotent on otel_trace_id: re-ingesting the same trace id for this organization
    replaces its spans rather than creating a duplicate trace row, since a real OTel
    exporter may retry a batch it is not sure was received."""
    trace = await session.scalar(
        select(Trace).where(
            Trace.organization_id == organization_id, Trace.otel_trace_id == otel_trace_id
        )
    )
    if trace is None:
        trace = Trace(
            organization_id=organization_id,
            otel_trace_id=otel_trace_id,
            evaluation_run_id=evaluation_run_id,
            test_case_id=test_case_id,
        )
        session.add(trace)
        await session.flush()
    else:
        await session.execute(delete(Span).where(Span.trace_id == trace.id))

    for span_in in spans_in:
        span = Span(
            trace_id=trace.id,
            otel_span_id=span_in.otel_span_id,
            parent_otel_span_id=span_in.parent_otel_span_id,
            name=span_in.name,
            gen_ai_operation_name=span_in.gen_ai_operation_name,
            started_at=span_in.started_at,
            ended_at=span_in.ended_at,
            status=span_in.status,
            attributes=span_in.attributes,
        )
        session.add(span)
        await session.flush()
        tool_call = _extract_tool_call(span)
        if tool_call is not None:
            session.add(tool_call)

    await session.commit()
    return await _trace_out(session, trace)


async def get_trace(
    session: AsyncSession, organization_id: uuid.UUID, trace_id: uuid.UUID
) -> TraceOut:
    trace = await session.get(Trace, trace_id)
    if trace is None or trace.organization_id != organization_id:
        raise NotFoundError("Trace not found")
    return await _trace_out(session, trace)


async def get_trace_for_run_and_case(
    session: AsyncSession,
    organization_id: uuid.UUID,
    evaluation_run_id: uuid.UUID,
    test_case_id: uuid.UUID,
) -> TraceOut | None:
    """The link AC6 requires in the other direction: given a score, find its matching
    trace. Returns None rather than raising, since a deterministic-only result may have
    no trace of its own (see evaluation_results.trace_id's nullability)."""
    trace = await session.scalar(
        select(Trace).where(
            Trace.organization_id == organization_id,
            Trace.evaluation_run_id == evaluation_run_id,
            Trace.test_case_id == test_case_id,
        )
    )
    if trace is None:
        return None
    return await _trace_out(session, trace)


async def tool_calls_for_span(session: AsyncSession, span_id: uuid.UUID) -> list[ToolCall]:
    rows = await session.scalars(select(ToolCallRecord).where(ToolCallRecord.span_id == span_id))
    return [ToolCall(name=r.tool_name, arguments=r.arguments) for r in rows]


async def tool_calls_for_trace(session: AsyncSession, trace_id: uuid.UUID) -> list[ToolCall]:
    """Every tool call across every span in a trace, the shape evaluators.schema.AgentOutput
    expects, so the worker can build one AgentOutput from a trace it just recorded."""
    span_ids = (await session.scalars(select(Span.id).where(Span.trace_id == trace_id))).all()
    if not span_ids:
        return []
    rows = await session.scalars(select(ToolCallRecord).where(ToolCallRecord.span_id.in_(span_ids)))
    return [ToolCall(name=r.tool_name, arguments=r.arguments) for r in rows]


def utcnow() -> datetime:
    return datetime.now(UTC)
