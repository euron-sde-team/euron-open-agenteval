"""Sign-in with per-account lockout, and password changes that end every other session."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.audit.service import Actor, audit
from agenteval.core.errors import AppError, AuthenticationError
from agenteval.core.security import hash_password, password_problems, verify_password
from agenteval.users.models import User
from agenteval.users.service import get_by_email

MAX_FAILURES = 5
LOCKOUT = timedelta(minutes=15)


async def authenticate(session: AsyncSession, email: str, password: str, ip: str | None) -> User:
    user = await get_by_email(session, email)
    now = datetime.now(UTC)
    if user is not None and user.locked_until and user.locked_until > now:
        raise AuthenticationError(
            "Too many failed attempts. Try again in a few minutes", code="account_locked"
        )
    if not verify_password(password, user.password_hash if user else None) or user is None:
        if user is not None:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILURES:
                user.locked_until = now + LOCKOUT
                user.failed_logins = 0
            await session.commit()
        raise AuthenticationError("Email or password is incorrect", code="invalid_credentials")
    if user.disabled:
        raise AuthenticationError("This account is disabled", code="account_disabled")
    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = now
    audit(session, Actor(user.id, user.email, ip=ip), "auth.login", "user", user.id)
    await session.commit()
    return user


async def change_password(
    session: AsyncSession, user: User, current: str, new: str, actor: Actor
) -> User:
    if not verify_password(current, user.password_hash):
        raise AuthenticationError("Current password is incorrect", code="invalid_credentials")
    if problems := password_problems(new):
        raise AppError(
            "Password needs " + ", ".join(problems),
            code="weak_password",
            details={"problems": problems},
        )
    user.password_hash = hash_password(new)
    user.session_version += 1
    audit(session, actor, "auth.password_changed", "user", user.id)
    await session.commit()
    return user
