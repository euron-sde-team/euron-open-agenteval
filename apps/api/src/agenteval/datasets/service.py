"""Datasets: creation and versioning (AC10). Editing a dataset's test cases creates a
new DatasetVersion row rather than mutating the existing one, so an EvaluationRun's
dataset_version_id keeps pointing at the exact test cases it actually ran against, even
after a later edit."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.audit.service import Actor, audit
from agenteval.core.errors import ConflictError, NotFoundError
from agenteval.datasets.models import Dataset, DatasetVersion, TestCase
from agenteval.datasets.schemas import DatasetOut, DatasetVersionOut, TestCaseIn, TestCaseOut


@dataclass(frozen=True, slots=True)
class ResolvedTestCase:
    """What the evaluations domain needs to run a dataset version: just the id and the
    expected_behavior/input shape, decoupled from the API's own request schema."""

    id: uuid.UUID
    input: dict[str, object]
    expected_behavior: dict[str, object]


async def _test_case_count(session: AsyncSession, dataset_version_id: uuid.UUID) -> int:
    return (
        await session.scalar(
            select(func.count())
            .select_from(TestCase)
            .where(TestCase.dataset_version_id == dataset_version_id)
        )
    ) or 0


async def dataset_out(
    session: AsyncSession, dataset: Dataset, version: DatasetVersion
) -> DatasetOut:
    count = await _test_case_count(session, version.id)
    return DatasetOut(
        id=dataset.id,
        organization_id=dataset.organization_id,
        name=dataset.name,
        current_version_id=version.id,
        current_version_number=version.version_number,
        test_case_count=count,
        created_at=dataset.created_at,
    )


def _version_out(version: DatasetVersion, test_case_count: int) -> DatasetVersionOut:
    return DatasetVersionOut(
        id=version.id,
        dataset_id=version.dataset_id,
        version_number=version.version_number,
        test_case_count=test_case_count,
        created_at=version.created_at,
    )


async def _write_test_cases(
    session: AsyncSession, dataset_version_id: uuid.UUID, cases: list[TestCaseIn]
) -> None:
    for case in cases:
        session.add(
            TestCase(
                dataset_version_id=dataset_version_id,
                input=case.input,
                expected_behavior=case.expected_behavior.model_dump(),
                tags=case.tags,
            )
        )


async def create_dataset(
    session: AsyncSession,
    organization_id: uuid.UUID,
    name: str,
    test_cases: list[TestCaseIn],
    actor: Actor,
) -> DatasetOut:
    existing = await session.scalar(
        select(Dataset).where(Dataset.organization_id == organization_id, Dataset.name == name)
    )
    if existing is not None:
        raise ConflictError(f"A dataset named {name!r} already exists in this organization")
    dataset = Dataset(organization_id=organization_id, name=name)
    session.add(dataset)
    await session.flush()
    version = DatasetVersion(dataset_id=dataset.id, version_number=1)
    session.add(version)
    await session.flush()
    await _write_test_cases(session, version.id, test_cases)
    audit(session, actor, "dataset.created", "dataset", dataset.id, name=name)
    await session.commit()
    return await dataset_out(session, dataset, version)


async def get_dataset(
    session: AsyncSession, organization_id: uuid.UUID, dataset_id: uuid.UUID
) -> tuple[Dataset, DatasetVersion]:
    dataset = await session.get(Dataset, dataset_id)
    if dataset is None or dataset.organization_id != organization_id:
        raise NotFoundError("Dataset not found")
    version = await session.scalar(
        select(DatasetVersion)
        .where(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version_number.desc())
        .limit(1)
    )
    assert version is not None  # every dataset is created with a first version
    return dataset, version


async def list_datasets(session: AsyncSession, organization_id: uuid.UUID) -> list[DatasetOut]:
    datasets = await session.scalars(
        select(Dataset).where(Dataset.organization_id == organization_id).order_by(Dataset.name)
    )
    out = []
    for dataset in datasets:
        _, version = await get_dataset(session, organization_id, dataset.id)
        out.append(await dataset_out(session, dataset, version))
    return out


async def create_dataset_version(
    session: AsyncSession,
    organization_id: uuid.UUID,
    dataset_id: uuid.UUID,
    test_cases: list[TestCaseIn],
    actor: Actor,
) -> DatasetVersionOut:
    dataset, current_version = await get_dataset(session, organization_id, dataset_id)
    new_version = DatasetVersion(
        dataset_id=dataset.id, version_number=current_version.version_number + 1
    )
    session.add(new_version)
    await session.flush()
    await _write_test_cases(session, new_version.id, test_cases)
    audit(
        session,
        actor,
        "dataset.version_created",
        "dataset",
        dataset.id,
        version_number=new_version.version_number,
    )
    await session.commit()
    return _version_out(new_version, len(test_cases))


async def list_test_cases(
    session: AsyncSession, dataset_version_id: uuid.UUID
) -> list[TestCaseOut]:
    rows = await session.scalars(
        select(TestCase)
        .where(TestCase.dataset_version_id == dataset_version_id)
        .order_by(TestCase.created_at)
    )
    return [
        TestCaseOut(
            id=r.id,
            input=r.input,
            expected_behavior=r.expected_behavior,
            tags=r.tags,
            created_at=r.created_at,
        )
        for r in rows
    ]


async def resolve_test_cases(
    session: AsyncSession, dataset_version_id: uuid.UUID
) -> list[ResolvedTestCase]:
    """The evaluations domain's own entry point: just enough of a test case to build an
    EvaluationCase, never the full API-shaped TestCaseOut."""
    rows = await session.scalars(
        select(TestCase)
        .where(TestCase.dataset_version_id == dataset_version_id)
        .order_by(TestCase.created_at)
    )
    return [
        ResolvedTestCase(id=r.id, input=r.input, expected_behavior=r.expected_behavior)
        for r in rows
    ]
