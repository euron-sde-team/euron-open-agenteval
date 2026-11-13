from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from agenteval.audit.models import AuditLog
from agenteval.audit.schemas import AuditLogOut
from agenteval.core.deps import SessionDep
from agenteval.orgs.dependencies import Admin

router = APIRouter(prefix="/api/v1/orgs/{org_id}/audit-log", tags=["audit"])


@router.get("", response_model=list[AuditLogOut], summary="This organization's audit log")
async def list_audit_log(
    org_id: uuid.UUID, _: Admin, session: SessionDep, limit: int = 100
) -> list[AuditLog]:
    rows = await session.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == org_id)
        .order_by(AuditLog.at.desc())
        .limit(min(limit, 500))
    )
    return list(rows.all())
