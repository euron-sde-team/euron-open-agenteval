"""SQLAlchemy models for the agents domain: a registered agent and its versions, so a
benchmark compares specific agent versions, not just whatever is currently registered
(docs/PLAN.md's scope section). The router/service layer for this domain is a later
phase; the models exist now so the full 0.1.0 schema is one migration, not several."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenteval.core.db import Base, TimestampMixin, new_id

AGENT_ADAPTER_TYPES = ("http", "python", "recorded")


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_agent_org_name"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False, default="other")


class AgentVersion(TimestampMixin, Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "label", name="uq_agent_version_label"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    # Adapter-specific configuration: an http adapter's endpoint URL, a python adapter's
    # import path, a recorded adapter has none (its traces are supplied by the caller).
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
