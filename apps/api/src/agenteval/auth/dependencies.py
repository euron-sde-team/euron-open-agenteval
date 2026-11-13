"""Dashboard authentication: session cookie (browser) or bearer session token (API or
CLI). Resolves WHO is making the request; WHAT they can do in a given organization is a
separate check (see orgs.service.require_membership), since role is per-organization, not
global.

Cookie-authenticated mutations must carry ``X-AgentEval-CSRF: 1``. Browsers cannot add a
custom header to a cross-site request without a CORS preflight, which the allowlist
refuses, so this blocks CSRF without server-side token state.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from agenteval.core.deps import ContainerDep, SessionDep, client_ip
from agenteval.core.errors import AuthenticationError, PermissionDeniedError
from agenteval.core.security import decode_session
from agenteval.users.models import User

SESSION_COOKIE = "ae_session"
CSRF_HEADER = "x-agenteval-csrf"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def current_user(request: Request, container: ContainerDep, session: SessionDep) -> User:
    # An explicit Authorization header wins: browsers never attach it cross-site, so it
    # needs no CSRF check. The cookie is the fallback for the dashboard.
    header = request.headers.get("authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else None
    via_cookie = False
    if not token:
        token = request.cookies.get(SESSION_COOKIE)
        via_cookie = token is not None
    if not token:
        raise AuthenticationError("Sign in to continue", code="not_signed_in")
    claims = decode_session(token, container.settings.session_secret)
    if claims is None:
        raise AuthenticationError("Your session expired. Sign in again", code="session_expired")
    user = await session.get(User, claims.user_id)
    if user is None or user.disabled or user.session_version != claims.session_version:
        raise AuthenticationError("Your session expired. Sign in again", code="session_expired")
    if (
        via_cookie
        and request.method not in _SAFE_METHODS
        and request.headers.get(CSRF_HEADER) != "1"
    ):
        raise PermissionDeniedError("Missing CSRF header", code="csrf_required")
    request.state.client_ip = client_ip(request)
    return user


CurrentUser = Annotated[User, Depends(current_user)]
