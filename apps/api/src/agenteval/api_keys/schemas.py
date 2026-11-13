"""Pydantic schemas for the api_keys domain."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from agenteval.core.schemas import ApiModel


class ApiKeyIn(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="member")
    expires_at: datetime | None = None


class ApiKeyOut(ApiModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    prefix: str
    display: str
    role: str
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiModel):
    key: ApiKeyOut
    plaintext: str  # shown exactly once, at creation
