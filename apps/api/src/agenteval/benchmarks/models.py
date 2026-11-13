"""SQLAlchemy model for the benchmarks domain: a computed, cached pairwise comparison
between two evaluation runs (docs/PLAN.md AC8). The router/service layer for this domain
is a later phase; the model exists now so the full 0.1.0 schema is one migration, not
several."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenteval.core.db import Base, new_id


class BenchmarkComparisonRecord(Base):
    """Named *Record* to avoid colliding with evaluators.schema.BenchmarkComparison, the
    pure dataclass compare.py actually computes; this is only its cached storage row."""

    __tablename__ = "benchmark_comparisons"
    __table_args__ = (
        UniqueConstraint(
            "baseline_run_id", "candidate_run_id", name="uq_benchmark_comparison_run_pair"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    baseline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False
    )
    candidate_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False
    )
    # The serialized list of BenchmarkDelta (metric_id, baseline_mean, candidate_mean,
    # delta, is_regression), recomputed if either run's results change (they should not,
    # once a run is complete), per docs/PLAN.md's caching layers table.
    deltas: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
