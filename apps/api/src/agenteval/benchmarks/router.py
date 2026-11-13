from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from agenteval.benchmarks import service
from agenteval.benchmarks.compare import DEFAULT_REGRESSION_THRESHOLD
from agenteval.benchmarks.schemas import BenchmarkComparisonOut, BenchmarkTrendOut
from agenteval.core.deps import SessionDep
from agenteval.orgs.dependencies import Viewer

router = APIRouter(tags=["benchmarks"])


@router.get(
    "/api/v1/orgs/{org_id}/benchmarks/compare",
    response_model=BenchmarkComparisonOut,
    summary="Pairwise comparison between two evaluation runs (AC8)",
)
async def compare(
    org_id: uuid.UUID,
    baseline_run_id: uuid.UUID,
    candidate_run_id: uuid.UUID,
    _: Viewer,
    session: SessionDep,
    regression_threshold: float = Query(DEFAULT_REGRESSION_THRESHOLD, gt=0, le=1),
) -> BenchmarkComparisonOut:
    return await service.compare(
        session, org_id, baseline_run_id, candidate_run_id, regression_threshold
    )


@router.get(
    "/api/v1/orgs/{org_id}/benchmarks/trend",
    response_model=BenchmarkTrendOut,
    summary="Each metric's mean score across a sequence of runs, oldest first (AC9)",
)
async def trend(
    org_id: uuid.UUID,
    _: Viewer,
    session: SessionDep,
    run_ids: list[uuid.UUID] = Query(...),
) -> BenchmarkTrendOut:
    return await service.get_trend(session, org_id, run_ids)
