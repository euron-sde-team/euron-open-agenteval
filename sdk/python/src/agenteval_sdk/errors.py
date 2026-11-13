"""The SDK's own error types, distinct from httpx's: a caller catching AgentEvalError
never needs to know this client is built on httpx underneath."""

from __future__ import annotations


class AgentEvalError(Exception):
    """Base class for every error this SDK raises on purpose."""


class AgentEvalApiError(AgentEvalError):
    """The server answered with a non-2xx response. Carries the status code and the
    server's own error body (if any) so a caller can distinguish, for example, a 404
    (AC13's tenant isolation) from a 422 (a bad request)."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"AgentEval API returned {status_code}: {body}")
        self.status_code = status_code
        self.body = body


class RunTimeoutError(AgentEvalError):
    """An evaluation run did not reach a terminal status (completed or failed) within
    the caller's own timeout. The run itself is untouched on the server: it may still
    finish; this only means the SDK stopped waiting for it."""

    def __init__(self, run_id: str, timeout_s: float) -> None:
        super().__init__(f"evaluation run {run_id} did not finish within {timeout_s}s")
        self.run_id = run_id
        self.timeout_s = timeout_s
