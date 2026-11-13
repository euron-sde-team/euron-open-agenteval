"""Pydantic schemas for the traces domain: OpenTelemetry GenAI semantic-convention
traces and spans, ingested verbatim (docs/PLAN.md's trace format section)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from agenteval.core.schemas import ApiModel


class SpanIn(ApiModel):
    otel_span_id: str = Field(min_length=1, max_length=16)
    parent_otel_span_id: str | None = None
    name: str
    gen_ai_operation_name: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "ok"
    attributes: dict[str, Any] = Field(default_factory=dict)


class TraceIngest(ApiModel):
    """A trace as any OpenTelemetry-compatible exporter would send it: a real
    ``otel_trace_id`` (32 hex chars) plus every span, never an AgentEval-invented id."""

    otel_trace_id: str = Field(min_length=32, max_length=32)
    evaluation_run_id: uuid.UUID | None = None
    test_case_id: uuid.UUID | None = None
    spans: list[SpanIn] = Field(default_factory=list)


class SpanOut(ApiModel):
    id: uuid.UUID
    otel_span_id: str
    parent_otel_span_id: str | None
    name: str
    gen_ai_operation_name: str | None
    started_at: datetime
    ended_at: datetime | None
    status: str
    attributes: dict[str, Any]


class TraceOut(ApiModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    otel_trace_id: str
    evaluation_run_id: uuid.UUID | None
    test_case_id: uuid.UUID | None
    spans: list[SpanOut]
    created_at: datetime
