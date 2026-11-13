"""Health, readiness and metrics."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from agenteval.core.deps import ContainerDep

router = APIRouter(tags=["system"])


@router.get("/healthz", summary="Liveness")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


async def _probe(name: str, coro: Any) -> tuple[str, dict[str, Any]]:
    t0 = time.perf_counter()
    try:
        await asyncio.wait_for(coro, timeout=2)
        return name, {"ok": True, "ms": round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as exc:
        return name, {"ok": False, "error": type(exc).__name__}


@router.get("/readyz", summary="Readiness: Postgres and Redis reachable")
async def readyz(container: ContainerDep, response: Response) -> dict[str, Any]:
    async def pg() -> None:
        async with container.db.engine.connect() as conn:
            await conn.execute(text("select 1"))

    checks = dict(
        await asyncio.gather(_probe("postgres", pg()), _probe("redis", container.redis.ping()))
    )
    ok = all(c["ok"] for c in checks.values())
    response.status_code = 200 if ok else 503
    return {"status": "ready" if ok else "degraded", "checks": checks}


@router.get("/metrics", summary="Prometheus metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
