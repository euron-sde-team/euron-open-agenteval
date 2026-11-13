"""Append-only audit trail. Written in the same transaction as the change it describes,
so a change without an audit row cannot be committed. Every evaluation run and every
reveal of a stored judge response goes through here (see docs/PLAN.md's security model)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.audit.models import AuditLog


@dataclass(frozen=True, slots=True)
class Actor:
    """``organization_id`` and ``role`` describe the organization context the action is
    scoped to (resolved by the route's own membership check): this product has no global
    role. Both are ``None`` for actions with no organization context, such as signing in
    or out, and an event recorded with ``organization_id=None`` never appears in any
    organization's audit log."""

    id: uuid.UUID | None
    email: str | None
    organization_id: uuid.UUID | None = None
    role: str | None = None
    ip: str | None = None


def audit(
    session: AsyncSession,
    actor: Actor,
    action: str,
    target_type: str | None = None,
    target_id: object | None = None,
    **details: Any,
) -> None:
    session.add(
        AuditLog(
            organization_id=actor.organization_id,
            actor_id=actor.id,
            actor_email=actor.email,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=details,
            ip=actor.ip,
        )
    )
