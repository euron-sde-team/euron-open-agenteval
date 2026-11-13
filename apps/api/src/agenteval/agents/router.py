from __future__ import annotations

import uuid

from fastapi import APIRouter

from agenteval.agents import service
from agenteval.agents.schemas import AgentIn, AgentOut, AgentVersionIn, AgentVersionOut
from agenteval.core.deps import SessionDep
from agenteval.orgs.dependencies import Member, Viewer

router = APIRouter(tags=["agents"])


@router.post("/api/v1/orgs/{org_id}/agents", response_model=AgentOut, summary="Register an agent")
async def register_agent(
    org_id: uuid.UUID, body: AgentIn, actor: Member, session: SessionDep
) -> AgentOut:
    return await service.register_agent(
        session, org_id, body.name, body.adapter_type, body.provider, actor
    )


@router.get(
    "/api/v1/orgs/{org_id}/agents",
    response_model=list[AgentOut],
    summary="Agents in this organization",
)
async def list_agents(org_id: uuid.UUID, _: Viewer, session: SessionDep) -> list[AgentOut]:
    return await service.list_agents(session, org_id)


@router.post(
    "/api/v1/orgs/{org_id}/agents/{agent_id}/versions",
    response_model=AgentVersionOut,
    summary="Register a new version of an agent",
)
async def create_agent_version(
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    body: AgentVersionIn,
    actor: Member,
    session: SessionDep,
) -> AgentVersionOut:
    return await service.create_agent_version(
        session, org_id, agent_id, body.label, body.config, actor
    )


@router.get(
    "/api/v1/orgs/{org_id}/agents/{agent_id}/versions",
    response_model=list[AgentVersionOut],
    summary="Versions of this agent",
)
async def list_agent_versions(
    org_id: uuid.UUID, agent_id: uuid.UUID, _: Viewer, session: SessionDep
) -> list[AgentVersionOut]:
    return await service.list_agent_versions(session, org_id, agent_id)
