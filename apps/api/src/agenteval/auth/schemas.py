"""Pydantic schemas for the auth domain."""

from __future__ import annotations

from agenteval.core.schemas import ApiModel, Email
from agenteval.users.schemas import UserOut


class LoginRequest(ApiModel):
    email: Email
    password: str


class PasswordChange(ApiModel):
    current_password: str
    new_password: str


class SessionOut(ApiModel):
    user: UserOut
    session_token: str
    expires_in_s: int
