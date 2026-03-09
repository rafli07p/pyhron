"""API contract models for the Enthropy trading platform.

Generic Pydantic v2 models used across all REST API endpoints to ensure
a consistent response envelope, pagination, error reporting, and health
check format.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorSeverity(StrEnum):
    """Severity levels for API errors."""

    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServiceStatus(StrEnum):
    """Health-check service status."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


# ---------------------------------------------------------------------------
# Response envelopes
# ---------------------------------------------------------------------------

class APIResponse[T](BaseModel):
    """Standard API response envelope.

    Every API endpoint returns data wrapped in this envelope so clients
    always see a predictable structure with ``success``, ``data``, and
    optional ``message`` / ``request_id`` fields.
    """

    model_config = {"str_strip_whitespace": True}

    success: bool = Field(default=True, description="Whether the request succeeded")
    data: T | None = Field(default=None, description="Response payload")
    message: str | None = Field(default=None, max_length=1024, description="Human-readable message")
    request_id: UUID = Field(default_factory=uuid4, description="Unique request trace identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp (UTC)")
    tenant_id: str | None = Field(default=None, max_length=64, description="Tenant context")

    @classmethod
    def ok(cls, data: T, *, message: str | None = None, tenant_id: str | None = None) -> APIResponse[T]:
        """Create a successful response."""
        return cls(success=True, data=data, message=message, tenant_id=tenant_id)

    @classmethod
    def fail(cls, message: str, *, tenant_id: str | None = None) -> APIResponse[None]:
        """Create a failed response with no data."""
        return cls(success=False, data=None, message=message, tenant_id=tenant_id)


class PaginatedResponse[T](BaseModel):
    """Paginated API response for list endpoints.

    Includes cursor-based and offset-based pagination metadata so
    clients can navigate large result sets efficiently.
    """

    model_config = {"str_strip_whitespace": True}

    success: bool = Field(default=True, description="Whether the request succeeded")
    data: list[T] = Field(default_factory=list, description="Page of results")
    total: int = Field(..., ge=0, description="Total number of matching records")
    page: int = Field(default=1, ge=1, description="Current page number (1-based)")
    page_size: int = Field(default=50, ge=1, le=1000, description="Number of records per page")
    has_next: bool = Field(default=False, description="Whether more pages are available")
    has_previous: bool = Field(default=False, description="Whether a previous page exists")
    next_cursor: str | None = Field(default=None, max_length=256, description="Cursor for next page (cursor-based)")
    request_id: UUID = Field(default_factory=uuid4, description="Unique request trace identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp (UTC)")
    tenant_id: str | None = Field(default=None, max_length=64, description="Tenant context")

    @property
    def total_pages(self) -> int:
        """Calculate total pages from total and page_size."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class ErrorDetail(BaseModel):
    """Structured detail for a single error."""

    model_config = {"frozen": True, "str_strip_whitespace": True}

    field: str | None = Field(default=None, max_length=256, description="Field that caused the error")
    code: str = Field(..., max_length=64, description="Machine-readable error code")
    message: str = Field(..., max_length=1024, description="Human-readable error message")
    severity: ErrorSeverity = Field(default=ErrorSeverity.ERROR, description="Error severity")


class ErrorResponse(BaseModel):
    """Standardised error response returned on 4xx / 5xx.

    Contains a top-level error code, human-readable message, and
    optional list of detailed field-level errors for validation
    failures.
    """

    model_config = {"str_strip_whitespace": True}

    success: bool = Field(default=False, description="Always False for error responses")
    error_code: str = Field(..., max_length=64, description="Machine-readable error code (e.g. VALIDATION_ERROR)")
    message: str = Field(..., max_length=2048, description="Human-readable error summary")
    details: list[ErrorDetail] = Field(default_factory=list, description="Field-level error details")
    request_id: UUID = Field(default_factory=uuid4, description="Unique request trace identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp (UTC)")
    path: str | None = Field(default=None, max_length=512, description="Request path that caused the error")
    tenant_id: str | None = Field(default=None, max_length=64, description="Tenant context")


class DependencyHealth(BaseModel):
    """Health status of a single downstream dependency."""

    model_config = {"frozen": True, "str_strip_whitespace": True}

    name: str = Field(..., max_length=64, description="Dependency name (e.g. 'postgres', 'redis')")
    status: ServiceStatus = Field(..., description="Dependency health status")
    latency_ms: float | None = Field(default=None, ge=0, description="Last probe latency in milliseconds")
    message: str | None = Field(default=None, max_length=256, description="Optional status message")


class HealthCheck(BaseModel):
    """Service health-check response.

    Returned by ``/health`` and ``/readiness`` endpoints.  Reports
    overall service status plus per-dependency breakdowns for
    operational monitoring.
    """

    model_config = {"str_strip_whitespace": True}

    service: str = Field(..., max_length=64, description="Service name")
    version: str = Field(..., max_length=32, description="Service version (semver)")
    status: ServiceStatus = Field(default=ServiceStatus.HEALTHY, description="Overall service status")
    uptime_seconds: float = Field(default=0.0, ge=0, description="Seconds since service started")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp (UTC)")
    dependencies: list[DependencyHealth] = Field(
        default_factory=list,
        description="Health of downstream dependencies",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary service metadata")

    @property
    def is_healthy(self) -> bool:
        """Return ``True`` when the service and all dependencies are healthy."""
        return self.status == ServiceStatus.HEALTHY and all(
            dep.status == ServiceStatus.HEALTHY for dep in self.dependencies
        )


__all__ = [
    "APIResponse",
    "DependencyHealth",
    "ErrorDetail",
    "ErrorResponse",
    "ErrorSeverity",
    "HealthCheck",
    "PaginatedResponse",
    "ServiceStatus",
]
