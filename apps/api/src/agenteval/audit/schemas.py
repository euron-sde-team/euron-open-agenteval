"""Pydantic schemas for the audit domain."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from agenteval.core.schemas import ApiModel


class AuditLogOut(ApiModel):
    id: int
    at: datetime
    organization_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    actor_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    details: dict[str, Any]
    ip: str | None
