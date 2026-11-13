"""Pydantic schemas for the evaluations domain."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from agenteval.core.schemas import ApiModel


class EvaluationRunIn(ApiModel):
    agent_version_id: uuid.UUID
    dataset_version_id: uuid.UUID
    metric_ids: list[str] = Field(min_length=1)


class EvaluationResultOut(ApiModel):
    id: uuid.UUID
    test_case_id: uuid.UUID
    trace_id: uuid.UUID | None
    metric_id: str
    method: str
    score: float
    passed: bool
    reasoning: str
    rubric_version: str | None
    judge_model: str | None
    judge_provider: str | None
    same_family_warning: bool
    created_at: datetime


class EvaluationRunOut(ApiModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    agent_version_id: uuid.UUID
    dataset_version_id: uuid.UUID
    status: str
    metric_ids: list[str]
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    created_at: datetime


class EvaluationRunDetailOut(EvaluationRunOut):
    results: list[EvaluationResultOut] = Field(default_factory=list)


class JudgeCallOut(ApiModel):
    """The raw request/response an evaluation result's judge-based metric produced,
    kept behind an explicit reveal endpoint rather than inlined into every result
    listing, the same "audited reveal" posture the sibling projects in this program use
    for anything sensitive-by-volume (AC4)."""

    id: uuid.UUID
    prompt: str
    raw_response: str
    created_at: datetime
