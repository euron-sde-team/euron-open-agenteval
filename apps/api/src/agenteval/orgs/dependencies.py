"""Resolve the organization-scoped actor for a request: who is acting, and with what role
in the specific organization the route targets. Every domain that scopes its data to an
organization (agents, datasets, evaluations, traces, benchmarks, api_keys) depends on
this rather than rolling its own membership check, so AC13's tenant isolation is enforced
in one place.

Two ways to authenticate an org-scoped request: a dashboard session cookie (resolved
against the user's membership for the path's organization) or an organization API key in
the ``Authorization`` header (which already belongs to exactly one organization and
carries its own role). A key is never usable against a different organization by editing
the URL: mismatching ``organization_id`` is reported identically to "no such organization".
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.api_keys.service import authenticate_key
from agenteval.audit.service import Actor
from agenteval.auth.dependencies import SESSION_COOKIE
from agenteval.core.deps import ContainerDep, SessionDep, client_ip
from agenteval.core.errors import AuthenticationError, NotFoundError, PermissionDeniedError
from agenteval.core.security import decode_session
from agenteval.orgs.service import require_membership, role_at_least
from agenteval.users.models import User

_OrgActorDependency = Callable[[Request, AsyncSession, ContainerDep, uuid.UUID], Awaitable[Actor]]


async def _actor_from_api_key(
    request: Request,
    session: AsyncSession,
    container: ContainerDep,
    org_id: uuid.UUID,
    raw_key: str,
    minimum_role: str,
) -> Actor:
    key = await authenticate_key(session, raw_key, container.settings.api_key_pepper)
    if key is None:
        raise AuthenticationError(
            "This API key is invalid, revoked or expired", code="invalid_api_key"
        )
    if key.organization_id != org_id:
        # Looks exactly like "no such organization", never "wrong key": AC13 again, this
        # time for a key probing a path it was never issued for.
        raise NotFoundError("Organization not found")
    if not role_at_least(key.role, minimum_role):
        raise PermissionDeniedError(f"This key needs the {minimum_role} role or higher")
    return Actor(None, None, org_id, key.role, client_ip(request))


async def _actor_from_session(
    request: Request,
    session: AsyncSession,
    container: ContainerDep,
    org_id: uuid.UUID,
    minimum_role: str,
) -> Actor:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AuthenticationError("Sign in to continue", code="not_signed_in")
    claims = decode_session(token, container.settings.session_secret)
    if claims is None:
        raise AuthenticationError("Your session expired. Sign in again", code="session_expired")
    user = await session.get(User, claims.user_id)
    if user is None or user.disabled or user.session_version != claims.session_version:
        raise AuthenticationError("Your session expired. Sign in again", code="session_expired")
    # require_membership already enforces minimum_role; nothing left to check here.
    membership = await require_membership(session, org_id, user.id, minimum_role=minimum_role)
    return Actor(user.id, user.email, org_id, membership.role, client_ip(request))


def org_actor(minimum_role: str = "viewer") -> _OrgActorDependency:
    """Build a dependency that resolves the path's ``org_id`` against either an API key
    or the signed-in user's membership, raising NotFoundError if the caller cannot see
    this organization at all (never PermissionDeniedError, which would confirm it exists)
    or PermissionDeniedError once membership or the key's role is confirmed too low."""

    async def dependency(
        request: Request,
        session: SessionDep,
        container: ContainerDep,
        org_id: Annotated[uuid.UUID, Path()],
    ) -> Actor:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer aek_"):
            return await _actor_from_api_key(
                request, session, container, org_id, header[7:].strip(), minimum_role
            )
        return await _actor_from_session(request, session, container, org_id, minimum_role)

    return dependency


Viewer = Annotated[Actor, Depends(org_actor("viewer"))]
Member = Annotated[Actor, Depends(org_actor("member"))]
Admin = Annotated[Actor, Depends(org_actor("admin"))]
Owner = Annotated[Actor, Depends(org_actor("owner"))]
