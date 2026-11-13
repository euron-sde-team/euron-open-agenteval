from __future__ import annotations

import uuid

from fastapi import APIRouter

from agenteval.api_keys import service
from agenteval.api_keys.schemas import ApiKeyCreated, ApiKeyIn, ApiKeyOut
from agenteval.core.deps import ContainerDep, SessionDep
from agenteval.core.schemas import Message
from agenteval.orgs.dependencies import Admin, Owner

router = APIRouter(prefix="/api/v1/orgs/{org_id}/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut], summary="API keys for this organization")
async def list_keys(
    org_id: uuid.UUID, _: Admin, session: SessionDep, include_revoked: bool = True
) -> list[ApiKeyOut]:
    # Revoked keys default to included, not hidden: the dashboard shows them dimmed
    # rather than deleting them from view, since "this key existed and was revoked" is
    # exactly what an admin auditing access wants to see, not just what is still live.
    return await service.list_keys(session, org_id, include_revoked=include_revoked)


@router.post("", response_model=ApiKeyCreated, summary="Create an API key")
async def create_key(
    org_id: uuid.UUID, body: ApiKeyIn, actor: Admin, session: SessionDep, container: ContainerDep
) -> ApiKeyCreated:
    return await service.create_key(
        session,
        org_id,
        body.name,
        body.role,
        body.expires_at,
        container.settings.api_key_pepper,
        actor,
    )


@router.delete("/{key_id}", response_model=Message, summary="Revoke an API key")
async def revoke_key(
    org_id: uuid.UUID, key_id: uuid.UUID, actor: Owner, session: SessionDep
) -> Message:
    await service.revoke_key(session, org_id, key_id, actor)
    return Message(message="API key revoked")
