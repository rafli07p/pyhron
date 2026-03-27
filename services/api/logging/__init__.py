"""Pyhron Structured Logging.

Provides ``configure_logging`` to set up structlog with JSON output
(ELK-compatible), plus FastAPI middleware for request logging and
audit logging of mutations.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import UTC, datetime, timezone
from typing import Any

import structlog
from fastapi import Request
from structlog.types import EventDict, WrappedLogger

# JSON log formatter (ELK / Elasticsearch compatible)


class ELKJSONRenderer(structlog.dev.ConsoleRenderer):
    """Custom JSON renderer that outputs ELK-compatible log records.

    Produces JSON lines with ``@timestamp``, ``level``, ``message``,
    ``logger``, ``service``, and any extra fields from the structlog
    event dict.
    """

    def __init__(self, service_name: str = "pyhron") -> None:
        self._service_name = service_name

    def __call__(self, logger_obj: WrappedLogger, name: str, event_dict: EventDict) -> str:
        import json as _json

        record: dict[str, Any] = {
            "@timestamp": datetime.now(tz=UTC).isoformat(),
            "level": event_dict.pop("level", name).upper(),
            "message": event_dict.pop("event", ""),
            "logger": event_dict.pop("logger", ""),
            "service": self._service_name,
        }
        # Flatten remaining keys
        record.update(event_dict)
        return _json.dumps(record, default=str)


# configure_logging


def configure_logging(
    *,
    level: str = "INFO",
    json_output: bool = True,
    service_name: str = "pyhron",
) -> None:
    """Configure structlog and stdlib logging for the application.

    Parameters
    ----------
    level:
        Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    json_output:
        When ``True`` (default), use JSON renderer for ELK ingestion.
        When ``False``, use the human-readable console renderer.
    service_name:
        Name embedded in every JSON log line for ELK filtering.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        structlog.processors.JSONRenderer(default=str)
    else:
        structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            ELKJSONRenderer(service_name=service_name) if json_output else structlog.dev.ConsoleRenderer(),
        ],
        foreign_pre_chain=shared_processors,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore", "websockets"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# RequestLoggingMiddleware


class RequestLoggingMiddleware:
    """ASGI middleware that logs every HTTP request with timing.

    Captures method, path, status code, duration, client IP, and
    user-agent.  Outputs via structlog for consistent JSON formatting.
    """

    def __init__(self, app: Any, *, service_name: str = "pyhron") -> None:
        self.app = app
        self._service_name = service_name
        self._logger = structlog.stdlib.get_logger("http.access")

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        start = time.perf_counter()
        response_status = 500
        response_content_length: int | None = None

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal response_status, response_content_length
            if message["type"] == "http.response.start":
                response_status = message["status"]
                headers = dict(message.get("headers", []))
                cl = headers.get(b"content-length")
                if cl:
                    response_content_length = int(cl)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                query=str(request.query_params) if request.query_params else None,
                status=response_status,
                duration_ms=round(elapsed_ms, 2),
                content_length=response_content_length,
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                service=self._service_name,
            )


# AuditLogMiddleware

_MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class AuditLogMiddleware:
    """ASGI middleware that logs mutation requests for audit trail.

    Captures POST, PUT, PATCH, and DELETE requests with tenant/user
    context extracted from the JWT Authorization header.  The request
    body is logged at DEBUG level only to avoid leaking sensitive data
    at INFO.
    """

    def __init__(self, app: Any) -> None:
        self.app = app
        self._logger = structlog.stdlib.get_logger("audit")

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        if request.method not in _MUTATION_METHODS:
            await self.app(scope, receive, send)
            return

        # Extract user context from JWT (best effort, don't block on failure)
        tenant_id: str | None = None
        user_id: str | None = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                import jwt as _jwt

                payload = _jwt.decode(
                    auth_header.removeprefix("Bearer ").strip(),
                    options={"verify_signature": False},  # audit middleware doesn't enforce auth
                )
                tenant_id = payload.get("tenant_id")
                user_id = payload.get("sub")
            except Exception:
                pass

        start = time.perf_counter()
        response_status = 500

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._logger.info(
                "audit_mutation",
                method=request.method,
                path=request.url.path,
                status=response_status,
                duration_ms=round(elapsed_ms, 2),
                tenant_id=tenant_id,
                user_id=user_id,
                client_ip=request.client.host if request.client else None,
            )


__all__ = [
    "AuditLogMiddleware",
    "ELKJSONRenderer",
    "RequestLoggingMiddleware",
    "configure_logging",
]
