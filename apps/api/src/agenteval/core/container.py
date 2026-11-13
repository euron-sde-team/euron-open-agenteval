"""Process-wide services, built once in the app lifespan and shared by every request.

Holding them in one object (on ``app.state``) instead of module globals keeps the app
factory re-entrant and lets tests build an isolated container per app.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from redis.asyncio import Redis

from agenteval.core.config import Settings
from agenteval.core.db import Database
from agenteval.core.redis_client import create_redis


@dataclass
class Container:
    settings: Settings
    db: Database
    redis: Redis
    http: httpx.AsyncClient

    @classmethod
    def build(cls, settings: Settings) -> Container:
        redis = create_redis(settings.redis_url)
        # Shared by judge-provider calls (the evaluators package's judge metrics) and
        # agent http-adapter calls (invoking a registered agent's own endpoint); both are
        # short, synchronous HTTP calls, not long-lived streams.
        http = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
            follow_redirects=False,
        )
        return cls(
            settings=settings,
            db=Database(settings.database_url),
            redis=redis,
            http=http,
        )

    async def close(self) -> None:
        await self.http.aclose()
        await self.redis.aclose()
        await self.db.dispose()
