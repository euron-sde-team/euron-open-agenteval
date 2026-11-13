"""Pydantic schemas for the users domain."""

from __future__ import annotations

import uuid
from datetime import datetime

from agenteval.core.schemas import ApiModel


class UserOut(ApiModel):
    id: uuid.UUID
    email: str
    name: str
    disabled: bool
    last_login_at: datetime | None
    created_at: datetime
