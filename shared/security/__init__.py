"""Enthropy shared security module.

Re-exports authentication, RBAC, and audit logging utilities::

    from shared.security import create_access_token, require_role, AuditLogger
"""

from shared.security.audit import AuditAction, AuditLogger, AuditRecord, ExportFormat
from shared.security.auth import (
    TokenError,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from shared.security.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    Role,
    check_permission,
    require_permission,
    require_role,
    require_tenant,
)

__all__ = [
    # Auth
    "TokenError",
    "TokenPayload",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "hash_password",
    "verify_password",
    # RBAC
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    "check_permission",
    "require_permission",
    "require_role",
    "require_tenant",
    # Audit
    "AuditAction",
    "ExportFormat",
    "AuditRecord",
    "AuditLogger",
]
