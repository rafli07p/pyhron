"""Request tracing middleware for trace_id propagation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = structlog.stdlib.get_logger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Generate a trace_id (UUID) for each request.

    Injects into request state and response header X-Trace-ID.
    Sets structlog context so all log lines within the request
    include the trace_id automatically.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        request.state.trace_id = trace_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
