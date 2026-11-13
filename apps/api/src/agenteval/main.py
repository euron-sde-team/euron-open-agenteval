"""Application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from agenteval import __version__
from agenteval.agents.router import router as agents_router
from agenteval.api_keys.router import router as api_keys_router
from agenteval.audit.router import router as audit_router
from agenteval.auth.router import router as auth_router
from agenteval.benchmarks.router import router as benchmarks_router
from agenteval.core.config import Settings, get_settings
from agenteval.core.container import Container
from agenteval.core.db import import_all_models
from agenteval.core.errors import install_error_handlers
from agenteval.core.logs import configure_logging
from agenteval.core.middleware import RequestContextMiddleware
from agenteval.core.tracing import configure_tracing
from agenteval.datasets.router import router as datasets_router
from agenteval.evaluations.router import router as evaluations_router
from agenteval.orgs.router import router as orgs_router
from agenteval.system.router import router as system_router
from agenteval.traces.router import router as traces_router

DESCRIPTION = """
Score how well an AI agent completed a task, trace exactly how it got there, and track
whether a new model or prompt version made things better or worse.

Every endpoint is under `/api/v1`, available to the dashboard with a session cookie and to
automation with an organization API key.
"""


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    configure_tracing(settings)
    import_all_models()  # every domain's models, not just whichever routers happen to
    # import them transitively; see worker.py's own call for the bug this prevents.

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container or Container.build(settings)
        try:
            yield
        finally:
            if container is None:
                await app.state.container.close()

    app = FastAPI(
        title="Euron Open AgentEval",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    install_error_handlers(app)
    for router in (
        auth_router,
        orgs_router,
        api_keys_router,
        audit_router,
        system_router,
        agents_router,
        datasets_router,
        evaluations_router,
        traces_router,
        benchmarks_router,
    ):
        app.include_router(router)

    app.add_middleware(GZipMiddleware, minimum_size=2048)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "authorization",
            "content-type",
            "x-agenteval-csrf",
            "x-request-id",
        ],
        expose_headers=["x-request-id"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)
    return app
