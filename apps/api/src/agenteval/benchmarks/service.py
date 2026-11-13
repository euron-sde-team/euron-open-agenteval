"""Wires benchmarks.compare's pure functions into storage: fetches two runs' metric
summaries from the evaluations domain, computes a comparison, and caches it (docs/PLAN.md's
caching layers table: recomputed if either run's results change, which they should not
once a run is complete)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.benchmarks.compare import DEFAULT_REGRESSION_THRESHOLD, compare_runs, trend
from agenteval.benchmarks.models import BenchmarkComparisonRecord
from agenteval.benchmarks.schemas import (
    BenchmarkComparisonOut,
    BenchmarkDeltaOut,
    BenchmarkTrendOut,
    BenchmarkTrendPointOut,
)
from agenteval.core.errors import NotFoundError
from agenteval.evaluations.service import get_run, metric_summaries


async def compare(
    session: AsyncSession,
    organization_id: uuid.UUID,
    baseline_run_id: uuid.UUID,
    candidate_run_id: uuid.UUID,
    regression_threshold: float = DEFAULT_REGRESSION_THRESHOLD,
) -> BenchmarkComparisonOut:
    baseline_run = await get_run(session, organization_id, baseline_run_id)
    candidate_run = await get_run(session, organization_id, candidate_run_id)
    baseline_summaries = await metric_summaries(session, baseline_run.id)
    candidate_summaries = await metric_summaries(session, candidate_run.id)

    comparison = compare_runs(
        str(baseline_run_id),
        baseline_summaries,
        str(candidate_run_id),
        candidate_summaries,
        regression_threshold=regression_threshold,
    )

    existing = await session.scalar(
        select(BenchmarkComparisonRecord).where(
            BenchmarkComparisonRecord.baseline_run_id == baseline_run_id,
            BenchmarkComparisonRecord.candidate_run_id == candidate_run_id,
        )
    )
    deltas_json = [
        {
            "metric_id": d.metric_id,
            "baseline_mean": d.baseline_mean,
            "candidate_mean": d.candidate_mean,
            "delta": d.delta,
            "is_regression": d.is_regression,
        }
        for d in comparison.deltas
    ]
    if existing is None:
        session.add(
            BenchmarkComparisonRecord(
                organization_id=organization_id,
                baseline_run_id=baseline_run_id,
                candidate_run_id=candidate_run_id,
                deltas=deltas_json,
                computed_at=datetime.now(UTC),
            )
        )
    else:
        existing.deltas = deltas_json
        existing.computed_at = datetime.now(UTC)
    await session.commit()

    return BenchmarkComparisonOut(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        deltas=[BenchmarkDeltaOut(**d) for d in deltas_json],
        has_regression=comparison.has_regression,
    )


async def get_trend(
    session: AsyncSession, organization_id: uuid.UUID, run_ids_oldest_first: list[uuid.UUID]
) -> BenchmarkTrendOut:
    if not run_ids_oldest_first:
        raise NotFoundError("No runs given")
    summaries_by_run = {}
    for run_id in run_ids_oldest_first:
        run = await get_run(session, organization_id, run_id)
        summaries_by_run[str(run.id)] = await metric_summaries(session, run.id)
    series = trend([str(r) for r in run_ids_oldest_first], summaries_by_run)
    return BenchmarkTrendOut(
        series={
            metric_id: [
                BenchmarkTrendPointOut(run_id=uuid.UUID(rid), mean_score=score)
                for rid, score in points
            ]
            for metric_id, points in series.items()
        }
    )
