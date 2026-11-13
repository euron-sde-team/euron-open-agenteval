"""SQLAlchemy models for the traces domain: OpenTelemetry GenAI semantic-convention
traces and spans (docs/PLAN.md's trace format section), never a bespoke schema, so any
OpenTelemetry-compatible exporter can send a trace with no AgentEval-specific SDK
required. The router/service layer (ingestion and query) for this domain is a later
phase; the models exist now so the full 0.1.0 schema is one migration, not several."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenteval.core.db import Base, TimestampMixin, new_id


class Trace(TimestampMixin, Base):
    __tablename__ = "traces"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # evaluation_runs is a later-phase domain; a nullable FK lets a trace exist (e.g.
    # ingested directly via OTLP) before an evaluation run references it, and lets an
    # evaluation result always find its matching trace by run_id (PLAN.md's trace format
    # section: opening a score always offers its trace, and vice versa).
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    test_case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    # The real OpenTelemetry trace id (32 hex chars), not this row's own primary key, so
    # a trace ingested via OTLP by any exporter is found by the same id it already has.
    otel_trace_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)


class Span(Base):
    __tablename__ = "spans"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("traces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    otel_span_id: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_otel_span_id: Mapped[str | None] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # gen_ai.operation.name per the OpenTelemetry GenAI semantic conventions: chat,
    # execute_tool, etc. Never a bespoke operation vocabulary.
    gen_ai_operation_name: Mapped[str | None] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    # Every gen_ai.* attribute this span carries (model, token counts, tool name and
    # arguments, and so on), stored verbatim: this is the one place the OTel GenAI
    # attribute namespace is preserved byte-for-byte, so nothing AgentEval-specific is
    # invented in place of the real convention.
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ToolCallRecord(Base):
    """A tool call extracted from a span's gen_ai.* attributes into its own row, so the
    tool_inspector domain (a later phase, docs/PLAN.md AC7) can score tool selection
    accuracy and argument validity by querying this table directly, never by re-parsing
    an agent's free-text output."""

    __tablename__ = "tool_calls"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    span_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(200), nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(String(2000))
