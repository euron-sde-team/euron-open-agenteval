"""Pydantic schemas for the agents domain."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from agenteval.agents.models import AGENT_ADAPTER_TYPES
from agenteval.core.schemas import ApiModel
from agenteval.evaluators.schema import ProviderFamily


class AgentIn(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    adapter_type: str
    provider: ProviderFamily = "other"

    @field_validator("adapter_type")
    @classmethod
    def _valid_adapter_type(cls, v: str) -> str:
        if v not in AGENT_ADAPTER_TYPES:
            raise ValueError(f"adapter_type must be one of {AGENT_ADAPTER_TYPES}")
        return v


class AgentOut(ApiModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    adapter_type: str
    provider: str
    created_at: datetime


class AgentVersionIn(ApiModel):
    """``config`` is adapter-specific: an http adapter's endpoint URL
    (``{"endpoint_url": "..."}``, a python adapter's import path
    (``{"import_path": "pkg.module:callable"}``), a recorded adapter needs no config at
    all, since its traces are supplied by the caller at evaluation time."""

    label: str = Field(min_length=1, max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)


class AgentVersionOut(ApiModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    label: str
    config: dict[str, Any]
    created_at: datetime
