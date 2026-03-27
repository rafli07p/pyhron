"""Audit logging for the Pyhron platform.

Provides an :class:`AuditLogger` that records user actions with full
context (who, what, when, tenant) using :pypi:`structlog`.  Supports
export to JSON and CSV for compliance reporting.

Usage::

    from shared.security.audit import AuditLogger

    logger = AuditLogger(service="order-service")
    logger.log_action(
        user_id="u-123",
        action="CREATE_ORDER",
        resource="order/ord-456",
        details={"symbol": "AAPL", "qty": 100},
        tenant_id="t-acme",
    )

    # Export for compliance
    records = logger.export_audit_log(format="json")
"""

from __future__ import annotations

import csv
import io
import json
import threading
from datetime import UTC, datetime, timezone
from enum import StrEnum, unique
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

import structlog

from shared.utils import PyhronJSONEncoder

if TYPE_CHECKING:
    from collections.abc import Sequence

# Enumerations

@unique
class AuditAction(StrEnum):
    """Standard audit action types."""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    ROLE_CHANGE = "ROLE_CHANGE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    EXPORT = "EXPORT"
    ORDER_SUBMIT = "ORDER_SUBMIT"
    ORDER_CANCEL = "ORDER_CANCEL"
    RISK_OVERRIDE = "RISK_OVERRIDE"


@unique
class ExportFormat(StrEnum):
    """Supported audit log export formats."""

    JSON = "json"
    CSV = "csv"


# Audit record

class AuditRecord:
    """Immutable audit log entry.

    Attributes:
        record_id: Unique identifier for this audit entry.
        timestamp: When the action occurred (UTC).
        user_id: Who performed the action.
        tenant_id: Which tenant context.
        action: What was done.
        resource: Which resource was affected.
        details: Additional context.
        ip_address: Client IP (if available).
        user_agent: Client user-agent (if available).
        service: Originating service name.
        success: Whether the action succeeded.
    """

    __slots__ = (
        "action",
        "details",
        "ip_address",
        "record_id",
        "resource",
        "service",
        "success",
        "tenant_id",
        "timestamp",
        "user_agent",
        "user_id",
    )

    def __init__(
        self,
        *,
        user_id: str,
        tenant_id: str,
        action: str,
        resource: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        service: str = "unknown",
        success: bool = True,
    ) -> None:
        self.record_id = str(uuid4())
        self.timestamp = datetime.now(tz=UTC)
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.action = action
        self.resource = resource
        self.details = details or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.service = service
        self.success = success

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record to a plain dictionary."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "action": self.action,
            "resource": self.resource,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "service": self.service,
            "success": self.success,
        }

    def __repr__(self) -> str:
        return (
            f"AuditRecord(id={self.record_id!r}, user={self.user_id!r}, "
            f"action={self.action!r}, resource={self.resource!r})"
        )


# Audit logger

class AuditLogger:
    """Structured audit logger with in-memory buffer and export support.

    In production, audit records should also be forwarded to a
    persistent store (e.g. PostgreSQL, Elasticsearch) via the
    ``on_record`` callback or by consuming the structlog output.

    Args:
        service: Name of the originating service.
        buffer_size: Maximum in-memory records before oldest are evicted.
        on_record: Optional callback invoked for every new record (e.g.
            to persist to a database asynchronously).
    """

    def __init__(
        self,
        service: str = "pyhron",
        buffer_size: int = 10_000,
        on_record: Any | None = None,
    ) -> None:
        self._service = service
        self._buffer_size = buffer_size
        self._on_record = on_record
        self._records: list[AuditRecord] = []
        self._lock = threading.Lock()
        self._logger = structlog.get_logger("audit").bind(service=service)

    # Core API

    def log_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        *,
        details: dict[str, Any] | None = None,
        tenant_id: str = "",
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
    ) -> AuditRecord:
        """Record an auditable action.

        Args:
            user_id: Identifier of the user performing the action.
            action: Action name (use :class:`AuditAction` constants).
            resource: Resource path / identifier (e.g. ``order/ord-123``).
            details: Arbitrary context dictionary.
            tenant_id: Tenant identifier.
            ip_address: Client IP address.
            user_agent: Client user-agent string.
            success: Whether the action succeeded.

        Returns:
            The created :class:`AuditRecord`.
        """
        record = AuditRecord(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource=resource,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            service=self._service,
            success=success,
        )

        # Structured log output
        self._logger.info(
            "audit_event",
            record_id=record.record_id,
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource=resource,
            success=success,
            details=details or {},
        )

        # Buffer management
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._buffer_size:
                self._records = self._records[-self._buffer_size :]

        # Callback for external persistence
        if self._on_record is not None:
            try:
                self._on_record(record)
            except Exception:
                self._logger.error(
                    "audit_callback_failed",
                    record_id=record.record_id,
                    exc_info=True,
                )

        return record

    # Query / export

    def get_records(
        self,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Retrieve buffered audit records with optional filters.

        Args:
            tenant_id: Filter by tenant.
            user_id: Filter by user.
            action: Filter by action type.
            limit: Maximum number of records to return.

        Returns:
            Matching records, newest first.
        """
        with self._lock:
            filtered = self._records[:]

        if tenant_id is not None:
            filtered = [r for r in filtered if r.tenant_id == tenant_id]
        if user_id is not None:
            filtered = [r for r in filtered if r.user_id == user_id]
        if action is not None:
            filtered = [r for r in filtered if r.action == action]

        # Return newest first, limited
        return list(reversed(filtered[-limit:]))

    def export_audit_log(
        self,
        *,
        format: str = "json",
        tenant_id: str | None = None,
        user_id: str | None = None,
        action: str | None = None,
        limit: int = 10_000,
    ) -> str:
        """Export audit records as JSON or CSV.

        Args:
            format: Export format (``"json"`` or ``"csv"``).
            tenant_id: Filter by tenant.
            user_id: Filter by user.
            action: Filter by action type.
            limit: Maximum records to export.

        Returns:
            Formatted string of audit records.

        Raises:
            ValueError: If *format* is unsupported.
        """
        records = self.get_records(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            limit=limit,
        )
        dicts = [r.to_dict() for r in records]

        fmt = ExportFormat(format.lower())

        if fmt == ExportFormat.JSON:
            return json.dumps(dicts, cls=PyhronJSONEncoder, indent=2)

        if fmt == ExportFormat.CSV:
            return self._to_csv(dicts)

        raise ValueError(f"Unsupported export format: {format}")

    def clear(self) -> int:
        """Clear the in-memory audit buffer.

        Returns:
            Number of records cleared.
        """
        with self._lock:
            count = len(self._records)
            self._records.clear()
        return count

    @property
    def record_count(self) -> int:
        """Number of records currently in the buffer."""
        with self._lock:
            return len(self._records)

    # Helpers

    @staticmethod
    def _to_csv(records: Sequence[dict[str, Any]]) -> str:
        """Convert a list of record dicts to CSV."""
        if not records:
            return ""

        output = io.StringIO()
        fieldnames = [
            "record_id",
            "timestamp",
            "user_id",
            "tenant_id",
            "action",
            "resource",
            "success",
            "ip_address",
            "user_agent",
            "service",
            "details",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for record in records:
            row = {**record}
            # Serialize details dict to JSON string for CSV column
            if isinstance(row.get("details"), dict):
                row["details"] = json.dumps(row["details"], cls=PyhronJSONEncoder)
            writer.writerow(row)

        return output.getvalue()


__all__ = [
    "AuditAction",
    "AuditLogger",
    "AuditRecord",
    "ExportFormat",
]
