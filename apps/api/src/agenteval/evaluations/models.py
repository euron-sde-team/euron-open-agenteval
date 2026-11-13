"""SQLAlchemy models for the evaluations domain: a queued and claimed run (Postgres
``FOR UPDATE SKIP LOCKED``, the same pattern every worker in this program uses), its
per-test-case per-metric results, the metric registry (built-in and custom, each with a
rubric version), and every judge call's raw request/response for audit (docs/PLAN.md
AC4). The router/service/worker-claiming layer for this domain is a later phase; the
models exist now so the full 0.1.0 schema is one migration, not several."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenteval.core.db import Base, TimestampMixin, new_id

EVALUATION_RUN_STATUSES = ("queued", "running", "completed", "failed")


class EvaluationRun(TimestampMixin, Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    metric_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    claimed_by: Mapped[str | None] = mapped_column(String(100))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: a deterministic check's result has no trace of its own to point at when
    # the agent produced no spans worth recording (e.g. a pure exact-match check against
    # a canned string); a judge-based or tool-calling result always sets this.
    trace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("traces.id", ondelete="SET NULL")
    )
    metric_id: Mapped[str] = mapped_column(String(100), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rubric_version: Mapped[str | None] = mapped_column(String(32))
    judge_model: Mapped[str | None] = mapped_column(String(100))
    judge_provider: Mapped[str | None] = mapped_column(String(16))
    same_family_warning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class JudgeCall(Base):
    """The raw request/response for every judge-based metric call, kept separately from
    EvaluationResult so the (potentially large) raw text never has to be loaded when
    only the score is needed, while still being retrievable for audit (AC4)."""

    __tablename__ = "judge_calls"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    evaluation_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Metric(TimestampMixin, Base):
    """The metric registry: built-in metrics are seeded rows (so a rubric_version change
    is a tracked row update, not just a constant buried in code) and custom metrics
    (AC11) are rows a user adds, picked up by the next evaluation run with no restart."""

    __tablename__ = "metrics"
    __table_args__ = (UniqueConstraint("organization_id", "metric_id", name="uq_metric_org_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    # Null for a built-in metric (shared across every organization); set for a
    # custom metric, which is this organization's own.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    metric_id: Mapped[str] = mapped_column(String(100), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    rubric_version: Mapped[str | None] = mapped_column(String(32))
    # A custom evaluator's definition: a rubric string (method="judge") or a reference to
    # a user-registered scoring function (method="deterministic"), picked up by the next
    # run with no restart (AC11).
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
