"""Structured JSON logging with a per-request id carried in a context variable."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

import orjson

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_RESERVED = set(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}
# A judge call's raw request/response is intentionally stored in Postgres for audit (see
# docs/PLAN.md), but it must never also leak into a log line incidentally; the key list
# below is deliberately generous about anything that could carry a credential or a
# judge/agent payload.
_REDACT = {
    "authorization",
    "api_key",
    "password",
    "secret",
    "secret_value",
    "plaintext",
    "token",
    "x-api-key",
    "raw_request",
    "raw_response",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = request_id_var.get()
        if rid:
            payload["request_id"] = rid
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = "[redacted]" if key.lower() in _REDACT else value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return orjson.dumps(payload, default=str).decode()


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for noisy in ("uvicorn.access", "urllib3", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
