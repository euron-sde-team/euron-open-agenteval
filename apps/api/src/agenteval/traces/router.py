from __future__ import annotations

import uuid

from fastapi import APIRouter

from agenteval.core.deps import SessionDep
from agenteval.core.errors import NotFoundError
from agenteval.orgs.dependencies import Member, Viewer
from agenteval.traces import service
from agenteval.traces.schemas import TraceIngest, TraceOut

router = APIRouter(tags=["traces"])


@router.post(
    "/api/v1/orgs/{org_id}/traces",
    response_model=TraceOut,
    summary="Ingest an OpenTelemetry GenAI trace",
)
async def ingest_trace(
    org_id: uuid.UUID, body: TraceIngest, _: Member, session: SessionDep
) -> TraceOut:
    return await service.ingest_trace(
        session,
        org_id,
        body.otel_trace_id,
        body.spans,
        evaluation_run_id=body.evaluation_run_id,
        test_case_id=body.test_case_id,
    )


@router.get("/api/v1/orgs/{org_id}/traces/{trace_id}", response_model=TraceOut, summary="One trace")
async def get_trace(
    org_id: uuid.UUID, trace_id: uuid.UUID, _: Viewer, session: SessionDep
) -> TraceOut:
    return await service.get_trace(session, org_id, trace_id)


@router.get(
    "/api/v1/orgs/{org_id}/evaluation-runs/{run_id}/test-cases/{test_case_id}/trace",
    response_model=TraceOut,
    summary="The trace matching one evaluation result, by run and test case (AC6)",
)
async def get_trace_for_run_and_case(
    org_id: uuid.UUID,
    run_id: uuid.UUID,
    test_case_id: uuid.UUID,
    _: Viewer,
    session: SessionDep,
) -> TraceOut:
    trace = await service.get_trace_for_run_and_case(session, org_id, run_id, test_case_id)
    if trace is None:
        raise NotFoundError("No trace was recorded for this run and test case")
    return trace
