from __future__ import annotations

import uuid

from fastapi import APIRouter

from agenteval.core.deps import SessionDep
from agenteval.datasets import service
from agenteval.datasets.schemas import (
    DatasetCreate,
    DatasetOut,
    DatasetVersionOut,
    DatasetVersionUpdate,
    TestCaseOut,
)
from agenteval.orgs.dependencies import Member, Viewer

router = APIRouter(tags=["datasets"])


@router.post(
    "/api/v1/orgs/{org_id}/datasets", response_model=DatasetOut, summary="Create a dataset"
)
async def create_dataset(
    org_id: uuid.UUID, body: DatasetCreate, actor: Member, session: SessionDep
) -> DatasetOut:
    return await service.create_dataset(session, org_id, body.name, body.test_cases, actor)


@router.get(
    "/api/v1/orgs/{org_id}/datasets",
    response_model=list[DatasetOut],
    summary="Datasets for this organization",
)
async def list_datasets(org_id: uuid.UUID, _: Viewer, session: SessionDep) -> list[DatasetOut]:
    return await service.list_datasets(session, org_id)


@router.get(
    "/api/v1/orgs/{org_id}/datasets/{dataset_id}", response_model=DatasetOut, summary="One dataset"
)
async def get_dataset(
    org_id: uuid.UUID, dataset_id: uuid.UUID, _: Viewer, session: SessionDep
) -> DatasetOut:
    dataset, version = await service.get_dataset(session, org_id, dataset_id)
    return await service.dataset_out(session, dataset, version)


@router.get(
    "/api/v1/orgs/{org_id}/datasets/{dataset_id}/test-cases",
    response_model=list[TestCaseOut],
    summary="The dataset's current version's test cases",
)
async def list_test_cases(
    org_id: uuid.UUID, dataset_id: uuid.UUID, actor: Viewer, session: SessionDep
) -> list[TestCaseOut]:
    del actor
    _dataset, version = await service.get_dataset(session, org_id, dataset_id)
    return await service.list_test_cases(session, version.id)


@router.post(
    "/api/v1/orgs/{org_id}/datasets/{dataset_id}/versions",
    response_model=DatasetVersionOut,
    summary="Replace this dataset's test cases, creating a new version (AC10)",
)
async def create_dataset_version(
    org_id: uuid.UUID,
    dataset_id: uuid.UUID,
    body: DatasetVersionUpdate,
    actor: Member,
    session: SessionDep,
) -> DatasetVersionOut:
    return await service.create_dataset_version(session, org_id, dataset_id, body.test_cases, actor)


@router.get(
    "/api/v1/orgs/{org_id}/dataset-versions/{dataset_version_id}/test-cases",
    response_model=list[TestCaseOut],
    summary="Test cases for one explicit dataset version (not necessarily the current one)",
)
async def list_test_cases_for_version(
    org_id: uuid.UUID, dataset_version_id: uuid.UUID, _: Viewer, session: SessionDep
) -> list[TestCaseOut]:
    return await service.get_test_cases_for_version(session, org_id, dataset_version_id)
