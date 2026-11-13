"""Integration harness: the real app in-process against real Postgres and Redis, with the
mock AI/LLM service served over real HTTP from a background thread.

    make test-integration      (starts Postgres and Redis containers if needed)

Safety: the suite truncates every table, so it refuses any database whose name does not
contain "test", and any non-local host unless ALLOW_REMOTE_TEST_DB=true.
"""

from __future__ import annotations

import asyncio
import os
import socket
import threading
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest
import uvicorn
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from agenteval.core.config import Settings
from agenteval.main import create_app

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://agenteval:agenteval@localhost:5742/agenteval_test",
)
TEST_REDIS = os.environ.get("TEST_REDIS_URL", "redis://localhost:5779/15")
OWNER = {"email": "owner@example.test", "password": "Owner-Pass-123"}
TABLES = (
    "benchmark_comparisons, judge_calls, evaluation_results, evaluation_runs, metrics, "
    "tool_calls, spans, traces, test_cases, dataset_versions, datasets, agent_versions, "
    "agents, audit_log, api_keys, memberships, organizations, users"
)


def _guard(url: str) -> None:
    parsed = urlparse(url.replace("+asyncpg", ""))
    if "test" not in (parsed.path or ""):
        raise RuntimeError(
            f"refusing to run against {parsed.path!r}: database name must contain 'test'"
        )
    if (
        parsed.hostname not in ("localhost", "127.0.0.1", "postgres")
        and os.environ.get("ALLOW_REMOTE_TEST_DB") != "true"
    ):
        raise RuntimeError("refusing a non-local test database (set ALLOW_REMOTE_TEST_DB=true)")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def mock_ai_url() -> Iterator[str]:
    port = _free_port()
    config = uvicorn.Config("mockllm.app:app", host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
async def database() -> AsyncIterator[str]:
    _guard(TEST_DB)
    admin_url = TEST_DB.rsplit("/", 1)[0] + "/postgres"
    name = TEST_DB.rsplit("/", 1)[1]
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    await engine.dispose()
    from agenteval.migrations.runner import upgrade

    await asyncio.to_thread(upgrade, TEST_DB)
    yield TEST_DB


@pytest.fixture
def settings(database: str, mock_ai_url: str) -> Settings:
    return Settings(
        environment="test",
        database_url=database,
        redis_url=TEST_REDIS,
        session_secret="test-only-session-secret-with-32-plus-bytes",
        api_key_pepper="test-only-api-key-pepper-with-32-plus-bytes",
        mock_ai_url=mock_ai_url,
    )


async def _reset(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    await engine.dispose()
    from redis.asyncio import Redis

    redis = Redis.from_url(settings.redis_url)
    await redis.flushdb()
    await redis.aclose()


@dataclass
class Api:
    """A signed-in owner client plus helpers for common setup."""

    client: httpx.AsyncClient
    app: FastAPI
    org_id: str
    mock_ai_url: str

    async def ok(self, method: str, path: str, json: Any = None, status: int | None = None) -> Any:
        resp = await self.client.request(method, path, json=json)
        expected = status or (201 if method == "POST" and resp.status_code == 201 else 200)
        assert resp.status_code == expected, f"{method} {path}: {resp.status_code} {resp.text}"
        return resp.json() if resp.content else None

    def anonymous_client(self) -> httpx.AsyncClient:
        """A fresh client against the same in-process app, with no session: for testing
        login itself and every "must not be signed in yet" path."""
        transport = httpx.ASGITransport(app=self.app)
        return httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=30)


async def _bootstrap_owner_and_org(settings: Settings) -> tuple[str, str]:
    from agenteval.core.db import Database
    from agenteval.core.security import hash_password
    from agenteval.orgs.models import Membership, Organization
    from agenteval.users.models import User

    db = Database(settings.database_url, pool_size=1, max_overflow=0)
    try:
        async with db.sessionmaker() as session:
            user = User(
                email=OWNER["email"], name="Owner", password_hash=hash_password(OWNER["password"])
            )
            session.add(user)
            await session.flush()
            org = Organization(name="Test Org", slug="test-org")
            session.add(org)
            await session.flush()
            session.add(Membership(organization_id=org.id, user_id=user.id, role="owner"))
            await session.commit()
            return str(user.id), str(org.id)
    finally:
        await db.dispose()


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    await _reset(settings)
    application = create_app(settings)
    async with LifespanManager(application, startup_timeout=60, shutdown_timeout=30):
        yield application


@pytest.fixture
async def api(app: FastAPI, settings: Settings, mock_ai_url: str) -> AsyncIterator[Api]:
    _, org_id = await _bootstrap_owner_and_org(settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", timeout=30
    ) as client:
        resp = await client.post("/api/v1/auth/login", json=OWNER)
        assert resp.status_code == 200, resp.text
        client.headers["authorization"] = f"Bearer {resp.json()['session_token']}"
        yield Api(client, app, org_id, mock_ai_url)
