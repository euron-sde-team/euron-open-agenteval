"""User accounts: creation and lookup. Sign-in and session handling live in auth/."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.errors import ConflictError
from agenteval.core.security import hash_password, password_problems
from agenteval.users.models import User


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(func.lower(User.email) == email.lower()))


async def create_user(session: AsyncSession, email: str, name: str, password: str) -> User:
    if await get_by_email(session, email) is not None:
        raise ConflictError("An account with this email already exists")
    if problems := password_problems(password):
        raise ConflictError("Password needs " + ", ".join(problems))
    user = User(email=email.lower(), name=name, password_hash=hash_password(password))
    session.add(user)
    await session.flush()
    return user
