"""Organizations and memberships: who belongs to which organization, with what role."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.audit.service import Actor, audit
from agenteval.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from agenteval.core.text import slugify
from agenteval.orgs.models import ORG_ROLES, Membership, Organization

_ROLE_RANK = {role: i for i, role in enumerate(("viewer", "member", "admin", "owner"))}


def role_at_least(role: str, minimum: str) -> bool:
    """True if ``role`` has at least the authority of ``minimum`` (owner > admin > member
    > viewer). Used everywhere a route needs "admin or above", not just an exact role."""
    return _ROLE_RANK.get(role, -1) >= _ROLE_RANK.get(minimum, 99)


async def unique_slug(session: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug, i = base, 2
    while await session.scalar(select(Organization.id).where(Organization.slug == slug)):
        slug, i = f"{base}-{i}", i + 1
    return slug


async def create_organization(
    session: AsyncSession, name: str, owner_user_id: uuid.UUID, actor: Actor
) -> Organization:
    org = Organization(name=name, slug=await unique_slug(session, name))
    session.add(org)
    await session.flush()
    session.add(Membership(organization_id=org.id, user_id=owner_user_id, role="owner"))
    audit(session, actor, "org.created", "organization", org.id, name=name)
    await session.commit()
    return org


async def get_membership(
    session: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> Membership | None:
    return await session.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id, Membership.user_id == user_id
        )
    )


async def require_membership(
    session: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    minimum_role: str = "viewer",
) -> Membership:
    """Raise NotFoundError, not PermissionDeniedError, for a user with no membership at
    all: AC13 requires another organization's resources to look like they do not exist,
    not that access was refused (which would confirm the organization exists)."""
    membership = await get_membership(session, organization_id, user_id)
    if membership is None:
        raise NotFoundError("Organization not found")
    if not role_at_least(membership.role, minimum_role):
        raise PermissionDeniedError(f"This action needs the {minimum_role} role or higher")
    return membership


async def list_members(session: AsyncSession, organization_id: uuid.UUID) -> list[Membership]:
    result = await session.scalars(
        select(Membership).where(Membership.organization_id == organization_id)
    )
    return list(result.all())


async def add_member(
    session: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    actor: Actor,
) -> Membership:
    if role not in ORG_ROLES:
        raise ConflictError(f"role must be one of {ORG_ROLES}")
    if await get_membership(session, organization_id, user_id) is not None:
        raise ConflictError("This user is already a member of this organization")
    membership = Membership(organization_id=organization_id, user_id=user_id, role=role)
    session.add(membership)
    audit(
        session,
        actor,
        "org.member_added",
        "organization",
        organization_id,
        user_id=str(user_id),
        role=role,
    )
    await session.commit()
    return membership


async def update_member_role(
    session: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID, role: str, actor: Actor
) -> Membership:
    if role not in ORG_ROLES:
        raise ConflictError(f"role must be one of {ORG_ROLES}")
    membership = await get_membership(session, organization_id, user_id)
    if membership is None:
        raise NotFoundError("Membership not found")
    if membership.role == "owner" and role != "owner":
        remaining_owners = await session.scalar(
            select(Membership.id).where(
                Membership.organization_id == organization_id,
                Membership.role == "owner",
                Membership.user_id != user_id,
            )
        )
        if remaining_owners is None:
            raise ConflictError("An organization must keep at least one owner")
    membership.role = role
    audit(
        session,
        actor,
        "org.member_role_changed",
        "organization",
        organization_id,
        user_id=str(user_id),
        role=role,
    )
    await session.commit()
    return membership


async def remove_member(
    session: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID, actor: Actor
) -> None:
    membership = await get_membership(session, organization_id, user_id)
    if membership is None:
        raise NotFoundError("Membership not found")
    if membership.role == "owner":
        remaining_owners = await session.scalar(
            select(Membership.id).where(
                Membership.organization_id == organization_id,
                Membership.role == "owner",
                Membership.user_id != user_id,
            )
        )
        if remaining_owners is None:
            raise ConflictError("An organization must keep at least one owner")
    await session.delete(membership)
    audit(
        session, actor, "org.member_removed", "organization", organization_id, user_id=str(user_id)
    )
    await session.commit()
