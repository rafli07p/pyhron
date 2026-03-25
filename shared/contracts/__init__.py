"""Pyhron shared contracts.

Re-exports API models, message types, and event priorities for
convenient access::

    from shared.contracts import APIResponse, MessageType, EventPriority
"""

from shared.contracts.api_models import (
    APIResponse,
    DependencyHealth,
    ErrorDetail,
    ErrorResponse,
    ErrorSeverity,
    HealthCheck,
    PaginatedResponse,
    ServiceStatus,
)
from shared.contracts.message_types import EventPriority, MessageType

__all__ = [
    # API models
    "APIResponse",
    "DependencyHealth",
    "ErrorDetail",
    "ErrorResponse",
    "ErrorSeverity",
    "EventPriority",
    "HealthCheck",
    # Message types
    "MessageType",
    "PaginatedResponse",
    "ServiceStatus",
]
