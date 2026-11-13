"""Agent registration and versioning: a benchmark compares specific agent VERSIONS, not
whatever is currently registered, so a version row is created once and never mutated."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.agents.models import Agent, AgentVersion
from agenteval.agents.schemas import AgentOut, AgentVersionOut
from agenteval.audit.service import Actor, audit
from agenteval.core.errors import ConflictError, NotFoundError


def _agent_out(agent: Agent) -> AgentOut:
    return AgentOut(
        id=agent.id,
        organization_id=agent.organization_id,
        name=agent.name,
        adapter_type=agent.adapter_type,
        provider=agent.provider,
        created_at=agent.created_at,
    )


def _version_out(version: AgentVersion) -> AgentVersionOut:
    return AgentVersionOut(
        id=version.id,
        agent_id=version.agent_id,
        label=version.label,
        config=version.config,
        created_at=version.created_at,
    )


async def register_agent(
    session: AsyncSession,
    organization_id: uuid.UUID,
    name: str,
    adapter_type: str,
    provider: str,
    actor: Actor,
) -> AgentOut:
    existing = await session.scalar(
        select(Agent).where(Agent.organization_id == organization_id, Agent.name == name)
    )
    if existing is not None:
        raise ConflictError(f"An agent named {name!r} already exists in this organization")
    agent = Agent(
        organization_id=organization_id, name=name, adapter_type=adapter_type, provider=provider
    )
    session.add(agent)
    await session.flush()
    audit(session, actor, "agent.registered", "agent", agent.id, name=name)
    await session.commit()
    return _agent_out(agent)


async def get_agent(
    session: AsyncSession, organization_id: uuid.UUID, agent_id: uuid.UUID
) -> Agent:
    agent = await session.get(Agent, agent_id)
    if agent is None or agent.organization_id != organization_id:
        raise NotFoundError("Agent not found")
    return agent


async def list_agents(session: AsyncSession, organization_id: uuid.UUID) -> list[AgentOut]:
    agents = await session.scalars(
        select(Agent).where(Agent.organization_id == organization_id).order_by(Agent.name)
    )
    return [_agent_out(a) for a in agents]


async def create_agent_version(
    session: AsyncSession,
    organization_id: uuid.UUID,
    agent_id: uuid.UUID,
    label: str,
    config: dict[str, object],
    actor: Actor,
) -> AgentVersionOut:
    agent = await get_agent(session, organization_id, agent_id)
    existing = await session.scalar(
        select(AgentVersion).where(AgentVersion.agent_id == agent.id, AgentVersion.label == label)
    )
    if existing is not None:
        raise ConflictError(f"Version {label!r} already exists for this agent")
    version = AgentVersion(agent_id=agent.id, label=label, config=config)
    session.add(version)
    await session.flush()
    audit(session, actor, "agent.version_created", "agent", agent.id, label=label)
    await session.commit()
    return _version_out(version)


async def list_agent_versions(
    session: AsyncSession, organization_id: uuid.UUID, agent_id: uuid.UUID
) -> list[AgentVersionOut]:
    await get_agent(session, organization_id, agent_id)
    versions = await session.scalars(
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.created_at)
    )
    return [_version_out(v) for v in versions]


async def get_agent_version(
    session: AsyncSession, organization_id: uuid.UUID, agent_version_id: uuid.UUID
) -> AgentVersion:
    version = await session.get(AgentVersion, agent_version_id)
    if version is None:
        raise NotFoundError("Agent version not found")
    await get_agent(session, organization_id, version.agent_id)  # raises if cross-org
    return version
