"""Organization API keys: create, list, revoke, and resolve one from its plaintext for
request authentication (see orgs/dependencies.py)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.api_keys.models import ApiKey
from agenteval.api_keys.schemas import ApiKeyCreated, ApiKeyOut
from agenteval.audit.service import Actor, audit
from agenteval.core.errors import ConflictError, NotFoundError
from agenteval.core.security import (
    constant_time_equals,
    generate_api_key,
    hash_key_secret,
    parse_api_key,
)
from agenteval.orgs.models import ORG_ROLES


def _to_out(key: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=key.id,
        organization_id=key.organization_id,
        name=key.name,
        prefix=key.prefix,
        display=f"aek_{key.prefix}_****",
        role=key.role,
        expires_at=key.expires_at,
        revoked_at=key.revoked_at,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
    )


async def list_keys(
    session: AsyncSession, organization_id: uuid.UUID, *, include_revoked: bool = False
) -> list[ApiKeyOut]:
    stmt = (
        select(ApiKey)
        .where(ApiKey.organization_id == organization_id)
        .order_by(ApiKey.created_at.desc())
    )
    if not include_revoked:
        stmt = stmt.where(ApiKey.revoked_at.is_(None))
    keys = await session.scalars(stmt)
    return [_to_out(k) for k in keys]


async def create_key(
    session: AsyncSession,
    organization_id: uuid.UUID,
    name: str,
    role: str,
    expires_at: datetime | None,
    pepper: str,
    actor: Actor,
) -> ApiKeyCreated:
    if role not in ORG_ROLES:
        raise ConflictError(f"role must be one of {ORG_ROLES}")
    generated = generate_api_key(pepper)
    key = ApiKey(
        organization_id=organization_id,
        name=name,
        prefix=generated.prefix,
        secret_hash=generated.secret_hash,
        role=role,
        expires_at=expires_at,
        created_by=actor.id,
    )
    session.add(key)
    await session.flush()
    audit(session, actor, "api_key.created", "api_key", key.id, name=name, role=role)
    await session.commit()
    return ApiKeyCreated(key=_to_out(key), plaintext=generated.plaintext)


async def revoke_key(
    session: AsyncSession, organization_id: uuid.UUID, key_id: uuid.UUID, actor: Actor
) -> None:
    key = await session.get(ApiKey, key_id)
    if key is None or key.organization_id != organization_id:
        raise NotFoundError("API key not found")
    if key.revoked_at is not None:
        return
    key.revoked_at = datetime.now(UTC)
    audit(session, actor, "api_key.revoked", "api_key", key.id, name=key.name)
    await session.commit()


async def authenticate_key(session: AsyncSession, raw_key: str, pepper: str) -> ApiKey | None:
    """Resolve a plaintext key to its row, or None if it is malformed, unknown, revoked,
    expired, or simply wrong (every one of those answers identically, so a caller cannot
    distinguish "wrong secret" from "unknown prefix" by timing or response shape)."""
    parsed = parse_api_key(raw_key)
    if parsed is None:
        return None
    prefix, secret = parsed
    key = await session.scalar(select(ApiKey).where(ApiKey.prefix == prefix))
    if key is None:
        return None
    if not constant_time_equals(hash_key_secret(secret, pepper), key.secret_hash):
        return None
    now = datetime.now(UTC)
    if key.revoked_at is not None or (key.expires_at is not None and key.expires_at <= now):
        return None
    key.last_used_at = now
    await session.commit()
    return key
