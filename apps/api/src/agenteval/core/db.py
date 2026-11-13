"""Database engine, session factory and the declarative base shared by every domain."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB, list[str]: JSONB}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Database:
    """Owns the engine and session factory for one application instance."""

    def __init__(self, url: str, *, pool_size: int = 10, max_overflow: int = 20) -> None:
        self.engine: AsyncEngine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessionmaker() as session:
            yield session

    async def dispose(self) -> None:
        await self.engine.dispose()


def import_all_models() -> None:
    """Import every domain's models so Base.metadata is complete (Alembic, tests)."""
    import agenteval.agents.models
    import agenteval.api_keys.models
    import agenteval.audit.models
    import agenteval.benchmarks.models
    import agenteval.datasets.models
    import agenteval.evaluations.models
    import agenteval.orgs.models
    import agenteval.traces.models
    import agenteval.users.models  # noqa: F401
