"""Pydantic schemas for the datasets domain."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from agenteval.core.schemas import ApiModel


class ExpectedBehaviorIn(ApiModel):
    """Matches evaluators.schema.ExpectedBehavior; a test case author sets only the
    fields that apply to this case, the rest stay unset and contribute no check."""

    description: str = ""
    exact_match: str | None = None
    regex: str | None = None
    json_schema: dict[str, Any] | None = None
    required_tool_calls: list[str] = Field(default_factory=list)
    forbidden_tool_calls: list[str] = Field(default_factory=list)


class TestCaseIn(ApiModel):
    input: dict[str, Any] = Field(default_factory=dict)
    expected_behavior: ExpectedBehaviorIn = Field(default_factory=ExpectedBehaviorIn)
    tags: list[str] = Field(default_factory=list)


class TestCaseOut(ApiModel):
    id: uuid.UUID
    input: dict[str, Any]
    expected_behavior: dict[str, Any]
    tags: list[str]
    created_at: datetime


class DatasetCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    test_cases: list[TestCaseIn] = Field(default_factory=list)


class DatasetOut(ApiModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    current_version_id: uuid.UUID
    current_version_number: int
    test_case_count: int
    created_at: datetime


class DatasetVersionOut(ApiModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    version_number: int
    test_case_count: int
    created_at: datetime


class DatasetVersionUpdate(ApiModel):
    """Replacing a dataset version's test cases creates a NEW version (AC10): past
    evaluation runs keep their dataset_version_id reference, so this request can never
    change what an already-completed run's score means."""

    test_cases: list[TestCaseIn] = Field(min_length=1)
