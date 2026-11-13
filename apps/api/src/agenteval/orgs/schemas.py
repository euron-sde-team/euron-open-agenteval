"""Pydantic schemas for the orgs domain."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from agenteval.core.schemas import ApiModel, Email
from agenteval.orgs.models import ORG_ROLES


class OrganizationOut(ApiModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    role: str  # the signed-in user's own role in this organization


class OrganizationCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)


class MembershipOut(ApiModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_name: str
    role: str
    created_at: datetime


class MemberInvite(ApiModel):
    email: Email
    role: str = Field(default="member")


class MemberRoleUpdate(ApiModel):
    role: str


def validate_role(role: str) -> str:
    if role not in ORG_ROLES:
        raise ValueError(f"role must be one of {ORG_ROLES}")
    return role
