from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from agenteval.audit.service import Actor
from agenteval.auth.dependencies import CurrentUser
from agenteval.core.deps import SessionDep
from agenteval.core.errors import ConflictError, NotFoundError
from agenteval.core.schemas import Message
from agenteval.orgs import service
from agenteval.orgs.dependencies import Admin, Owner, Viewer
from agenteval.orgs.models import Membership, Organization
from agenteval.orgs.schemas import (
    MemberInvite,
    MemberRoleUpdate,
    MembershipOut,
    OrganizationCreate,
    OrganizationOut,
)
from agenteval.orgs.service import list_members
from agenteval.users.service import get_by_email, get_user

router = APIRouter(prefix="/api/v1/orgs", tags=["orgs"])


def _org_out(org: Organization, role: str) -> OrganizationOut:
    return OrganizationOut(
        id=org.id, name=org.name, slug=org.slug, created_at=org.created_at, role=role
    )


@router.post("", response_model=OrganizationOut, summary="Create an organization")
async def create_organization(
    body: OrganizationCreate, user: CurrentUser, session: SessionDep
) -> OrganizationOut:
    org = await service.create_organization(session, body.name, user.id, Actor(user.id, user.email))
    return _org_out(org, "owner")


@router.get("", response_model=list[OrganizationOut], summary="Organizations you belong to")
async def list_my_organizations(user: CurrentUser, session: SessionDep) -> list[OrganizationOut]:
    rows = (
        await session.execute(
            select(Organization, Membership.role)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == user.id)
            .order_by(Organization.name)
        )
    ).all()
    return [_org_out(org, role) for org, role in rows]


@router.get("/{org_id}", response_model=OrganizationOut, summary="One organization")
async def get_organization(
    org_id: uuid.UUID, actor: Viewer, session: SessionDep
) -> OrganizationOut:
    org = await session.get(Organization, org_id)
    if org is None:
        raise NotFoundError("Organization not found")
    return _org_out(org, actor.role or "viewer")


@router.get(
    "/{org_id}/members", response_model=list[MembershipOut], summary="Members of this organization"
)
async def list_organization_members(
    org_id: uuid.UUID, _: Viewer, session: SessionDep
) -> list[MembershipOut]:
    memberships = await list_members(session, org_id)
    out: list[MembershipOut] = []
    for m in memberships:
        member_user = await get_user(session, m.user_id)
        if member_user is None:
            continue
        out.append(
            MembershipOut(
                id=m.id,
                user_id=m.user_id,
                user_email=member_user.email,
                user_name=member_user.name,
                role=m.role,
                created_at=m.created_at,
            )
        )
    return out


@router.post("/{org_id}/members", response_model=MembershipOut, summary="Invite a member")
async def invite_member(
    org_id: uuid.UUID, body: MemberInvite, actor: Admin, session: SessionDep
) -> MembershipOut:
    invited = await get_by_email(session, body.email)
    if invited is None:
        # Self-hosted and offline by design (see docs/PLAN.md): there is no invitation
        # email flow in 0.1.0. An admin creates the account directly with a temporary
        # password the invited person changes on first sign-in, the same way a CLI user
        # is created with `agenteval create-owner`.
        raise ConflictError(
            "No account with this email exists yet. Create the user's account first, "
            "then add them as a member"
        )
    membership = await service.add_member(session, org_id, invited.id, body.role, actor)
    return MembershipOut(
        id=membership.id,
        user_id=invited.id,
        user_email=invited.email,
        user_name=invited.name,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.patch(
    "/{org_id}/members/{user_id}", response_model=MembershipOut, summary="Change a member's role"
)
async def update_member_role(
    org_id: uuid.UUID, user_id: uuid.UUID, body: MemberRoleUpdate, actor: Admin, session: SessionDep
) -> MembershipOut:
    membership = await service.update_member_role(session, org_id, user_id, body.role, actor)
    member_user = await get_user(session, user_id)
    assert member_user is not None  # the membership we just updated references this user
    return MembershipOut(
        id=membership.id,
        user_id=user_id,
        user_email=member_user.email,
        user_name=member_user.name,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.delete("/{org_id}/members/{user_id}", response_model=Message, summary="Remove a member")
async def remove_member(
    org_id: uuid.UUID, user_id: uuid.UUID, actor: Owner, session: SessionDep
) -> Message:
    await service.remove_member(session, org_id, user_id, actor)
    return Message(message="Member removed")
