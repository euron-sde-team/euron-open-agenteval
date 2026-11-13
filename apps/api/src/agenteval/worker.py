"""The evaluation worker: claims queued evaluation runs (Postgres, ``FOR UPDATE SKIP
LOCKED``) and runs them. Any number of worker processes can run this loop concurrently.

This is a skeleton: the real claim-and-run logic (claiming an EvaluationRun row, invoking
the registered agent through its adapter, running deterministic and judge-based metrics,
writing EvaluationResult rows) is the evaluations domain's own service layer, a later
phase. This module exists now so ``agenteval worker`` is a real, runnable process from
the start, even before there is anything in the queue for it to claim.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import socket
import uuid

from agenteval.core.config import Settings, get_settings
from agenteval.core.container import Container
from agenteval.core.db import import_all_models
from agenteval.core.logs import configure_logging
from agenteval.core.tracing import configure_tracing

import_all_models()  # every domain's models must be registered before any cross-table
# foreign key is flushed; relying on whichever routers happened to import them is
# fragile, the exact bug this call prevents (see docs/PLAN.md's sibling projects' own
# notes on this in this program's memory).

log = logging.getLogger("agenteval.worker")

IDLE_POLL_S = 2.0


async def _poll_once(container: Container, worker_id: str) -> bool:
    """Claim and run at most one evaluation run. Returns True if one was claimed (so the
    caller polls again immediately instead of sleeping), False if the queue was empty.
    Until the evaluations domain's own claim_next_run exists, this always returns False:
    an idle worker, not a crashing one."""
    del container, worker_id  # unused until the evaluations domain's claim exists
    return False


async def main(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    configure_tracing(settings, service="agenteval-worker")
    container = Container.build(settings)
    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    log.info("worker.starting", extra={"worker_id": worker_id})

    stop = asyncio.Event()

    def _request_stop() -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    with contextlib.suppress(NotImplementedError):  # Windows has no add_signal_handler
        loop.add_signal_handler(signal.SIGTERM, _request_stop)
        loop.add_signal_handler(signal.SIGINT, _request_stop)

    try:
        while not stop.is_set():
            claimed = await _poll_once(container, worker_id)
            if not claimed:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=IDLE_POLL_S)
    finally:
        await container.close()
        log.info("worker.stopped", extra={"worker_id": worker_id})
