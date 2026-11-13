from __future__ import annotations

import uuid

from fastapi import APIRouter

from agenteval.core.deps import SessionDep
from agenteval.evaluations import service
from agenteval.evaluations.schemas import (
    EvaluationRunDetailOut,
    EvaluationRunIn,
    EvaluationRunOut,
    JudgeCallOut,
)
from agenteval.orgs.dependencies import Member, Owner, Viewer

router = APIRouter(tags=["evaluations"])


@router.post(
    "/api/v1/orgs/{org_id}/evaluation-runs",
    response_model=EvaluationRunOut,
    summary="Queue an evaluation run",
)
async def queue_run(
    org_id: uuid.UUID, body: EvaluationRunIn, actor: Member, session: SessionDep
) -> EvaluationRunOut:
    return await service.queue_run(
        session, org_id, body.agent_version_id, body.dataset_version_id, body.metric_ids, actor
    )


@router.post(
    "/api/v1/orgs/{org_id}/evaluation-runs/{run_id}/activate",
    response_model=EvaluationRunOut,
    summary="Make a pending (recorded-adapter) run claimable, once its traces are pushed",
)
async def activate_run(
    org_id: uuid.UUID, run_id: uuid.UUID, actor: Member, session: SessionDep
) -> EvaluationRunOut:
    return await service.activate_pending_run(session, org_id, run_id, actor)


@router.get(
    "/api/v1/orgs/{org_id}/evaluation-runs",
    response_model=list[EvaluationRunOut],
    summary="Evaluation runs for this organization",
)
async def list_runs(org_id: uuid.UUID, _: Viewer, session: SessionDep) -> list[EvaluationRunOut]:
    return await service.list_runs(session, org_id)


@router.get(
    "/api/v1/orgs/{org_id}/evaluation-runs/{run_id}",
    response_model=EvaluationRunDetailOut,
    summary="One evaluation run, with its per-test-case results",
)
async def get_run(
    org_id: uuid.UUID, run_id: uuid.UUID, _: Viewer, session: SessionDep
) -> EvaluationRunDetailOut:
    return await service.get_run_detail(session, org_id, run_id)


@router.get(
    "/api/v1/orgs/{org_id}/evaluation-results/{result_id}/judge-call",
    response_model=JudgeCallOut,
    summary="The raw judge request/response behind a judge-scored result (audited reveal, AC4)",
)
async def get_judge_call(
    org_id: uuid.UUID, result_id: uuid.UUID, _: Owner, session: SessionDep
) -> JudgeCallOut:
    return await service.get_judge_call(session, org_id, result_id)
