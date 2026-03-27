"""
Backup manager for the Pyhron data platform.

Provides scheduled backup logic for PostgreSQL (via ``pg_dump``) and
Redis (via ``BGSAVE`` / RDB copy).  Includes integrity verification
through SHA-256 checksums.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

# Constants
_MANIFEST_FILE = "backup_manifest.json"
_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB for checksum streaming


class BackupError(Exception):
    """Raised when a backup or restore operation fails."""


# BackupManager

class BackupManager:
    """Manage PostgreSQL and Redis backups for the Pyhron platform.

    Parameters
    ----------
    backup_dir : str | Path
        Root directory for storing backups.
    pg_connection_string : str | None
        PostgreSQL connection string (libpq format) for ``pg_dump`` /
        ``pg_restore``.  Example:
        ``postgresql://user:pass@host:5432/pyhron``.
    redis_rdb_path : str | Path | None
        Path to the Redis RDB dump file (e.g. ``/var/lib/redis/dump.rdb``).
    tenant_id : str
        Multi-tenancy identifier; backups are namespaced per tenant.
    pg_dump_path : str
        Absolute path to the ``pg_dump`` binary.
    pg_restore_path : str
        Absolute path to the ``pg_restore`` binary.
    """

    def __init__(
        self,
        backup_dir: str | Path = "/var/pyhron/backups",
        pg_connection_string: str | None = None,
        redis_rdb_path: str | Path | None = None,
        tenant_id: str = "default",
        pg_dump_path: str = "pg_dump",
        pg_restore_path: str = "pg_restore",
    ) -> None:
        self.tenant_id = tenant_id
        self._backup_root = Path(backup_dir) / tenant_id
        self._backup_root.mkdir(parents=True, exist_ok=True)

        self._pg_conn = pg_connection_string or os.environ.get("DATABASE_URL")
        self._redis_rdb = Path(redis_rdb_path) if redis_rdb_path else None
        self._pg_dump = pg_dump_path
        self._pg_restore = pg_restore_path

        self._log = logger.bind(tenant_id=tenant_id, component="BackupManager")
        self._log.info(
            "backup_manager_initialised",
            backup_dir=str(self._backup_root),
            has_pg=bool(self._pg_conn),
            has_redis=bool(self._redis_rdb),
        )

    # Create backup

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type(OSError),
        reraise=True,
    )
    async def create_backup(
        self,
        *,
        include_pg: bool = True,
        include_redis: bool = True,
        label: str | None = None,
        compression: bool = True,
    ) -> dict[str, Any]:
        """Create a new backup snapshot.

        Parameters
        ----------
        include_pg : bool
            Dump PostgreSQL via ``pg_dump``.
        include_redis : bool
            Copy the Redis RDB file.
        label : str | None
            Optional human-readable label.
        compression : bool
            When ``True`` the pg_dump uses ``--compress=6`` (zlib).

        Returns
        -------
        dict
            Backup manifest with paths, checksums, and metadata.
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_name = f"backup_{timestamp}"
        if label:
            backup_name += f"_{label}"
        backup_path = self._backup_root / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        manifest: dict[str, Any] = {
            "name": backup_name,
            "tenant_id": self.tenant_id,
            "created_at": datetime.now(UTC).isoformat(),
            "label": label,
            "components": {},
        }

        # PostgreSQL
        if include_pg and self._pg_conn:
            pg_file = backup_path / "pg_dump.sql.gz" if compression else backup_path / "pg_dump.sql"
            try:
                await self._run_pg_dump(pg_file, compression=compression)
                checksum = await asyncio.to_thread(self._sha256, pg_file)
                manifest["components"]["postgresql"] = {
                    "file": pg_file.name,
                    "size_bytes": pg_file.stat().st_size,
                    "sha256": checksum,
                }
                self._log.info("pg_backup_created", file=str(pg_file))
            except Exception as exc:
                self._log.error("pg_backup_failed", error=str(exc))
                manifest["components"]["postgresql"] = {"error": str(exc)}

        # Redis
        if include_redis and self._redis_rdb and self._redis_rdb.exists():
            redis_dest = backup_path / "redis_dump.rdb"
            try:
                await asyncio.to_thread(shutil.copy2, self._redis_rdb, redis_dest)
                checksum = await asyncio.to_thread(self._sha256, redis_dest)
                manifest["components"]["redis"] = {
                    "file": redis_dest.name,
                    "size_bytes": redis_dest.stat().st_size,
                    "sha256": checksum,
                }
                self._log.info("redis_backup_created", file=str(redis_dest))
            except Exception as exc:
                self._log.error("redis_backup_failed", error=str(exc))
                manifest["components"]["redis"] = {"error": str(exc)}

        # Write manifest
        manifest_path = backup_path / _MANIFEST_FILE
        manifest_path.write_text(json.dumps(manifest, indent=2))
        self._log.info("backup_created", name=backup_name)
        return manifest

    # Restore

    async def restore_backup(
        self,
        backup_name: str,
        *,
        restore_pg: bool = True,
        restore_redis: bool = True,
        verify_first: bool = True,
    ) -> dict[str, Any]:
        """Restore from a named backup.

        Parameters
        ----------
        backup_name : str
            Name of the backup directory under the tenant root.
        restore_pg : bool
            Restore the PostgreSQL dump.
        restore_redis : bool
            Copy the RDB file back to the Redis data directory.
        verify_first : bool
            Run integrity check before restoring.

        Returns
        -------
        dict
            Summary of the restore operation.
        """
        backup_path = self._backup_root / backup_name
        if not backup_path.exists():
            raise BackupError(f"Backup not found: {backup_name}")

        manifest = self._load_manifest(backup_path)

        if verify_first:
            integrity = await self.verify_backup_integrity(backup_name)
            if not integrity["valid"]:
                raise BackupError(
                    f"Integrity check failed: {integrity.get('errors')}"
                )

        result: dict[str, Any] = {"backup_name": backup_name, "restored": []}

        # PostgreSQL
        if restore_pg and "postgresql" in manifest.get("components", {}):
            pg_info = manifest["components"]["postgresql"]
            if "error" not in pg_info:
                pg_file = backup_path / pg_info["file"]
                try:
                    await self._run_pg_restore(pg_file)
                    result["restored"].append("postgresql")
                    self._log.info("pg_restored", file=str(pg_file))
                except Exception as exc:
                    self._log.error("pg_restore_failed", error=str(exc))
                    result["pg_error"] = str(exc)

        # Redis
        if restore_redis and "redis" in manifest.get("components", {}):
            redis_info = manifest["components"]["redis"]
            if "error" not in redis_info and self._redis_rdb:
                rdb_file = backup_path / redis_info["file"]
                try:
                    await asyncio.to_thread(shutil.copy2, rdb_file, self._redis_rdb)
                    result["restored"].append("redis")
                    self._log.info("redis_restored", dest=str(self._redis_rdb))
                except Exception as exc:
                    self._log.error("redis_restore_failed", error=str(exc))
                    result["redis_error"] = str(exc)

        self._log.info("backup_restored", **result)
        return result

    # List backups

    async def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups for this tenant.

        Returns a list of manifest dicts sorted newest-first.
        """
        backups: list[dict[str, Any]] = []
        if not self._backup_root.exists():
            return backups

        for entry in sorted(self._backup_root.iterdir(), reverse=True):
            if entry.is_dir():
                manifest_file = entry / _MANIFEST_FILE
                if manifest_file.exists():
                    try:
                        manifest = json.loads(manifest_file.read_text())
                        backups.append(manifest)
                    except json.JSONDecodeError:
                        self._log.warning("corrupt_manifest", path=str(manifest_file))
                else:
                    # Directory without manifest – include basic info
                    backups.append({
                        "name": entry.name,
                        "tenant_id": self.tenant_id,
                        "created_at": None,
                        "components": {},
                        "warning": "missing_manifest",
                    })

        self._log.debug("backups_listed", count=len(backups))
        return backups

    # Verify integrity

    async def verify_backup_integrity(self, backup_name: str) -> dict[str, Any]:
        """Verify SHA-256 checksums for all components in a backup.

        Returns
        -------
        dict
            ``{"valid": bool, "checked": [...], "errors": [...]}``
        """
        backup_path = self._backup_root / backup_name
        if not backup_path.exists():
            return {"valid": False, "errors": [f"Backup not found: {backup_name}"]}

        manifest = self._load_manifest(backup_path)
        checked: list[str] = []
        errors: list[str] = []

        for component, info in manifest.get("components", {}).items():
            if "error" in info:
                continue
            expected_hash = info.get("sha256")
            file_path = backup_path / info["file"]
            if not file_path.exists():
                errors.append(f"{component}: file missing ({info['file']})")
                continue
            actual_hash = await asyncio.to_thread(self._sha256, file_path)
            if actual_hash != expected_hash:
                errors.append(
                    f"{component}: checksum mismatch "
                    f"(expected {expected_hash[:16]}..., got {actual_hash[:16]}...)"
                )
            else:
                checked.append(component)

        valid = len(errors) == 0
        self._log.info(
            "backup_integrity_verified",
            backup=backup_name,
            valid=valid,
            checked=checked,
            error_count=len(errors),
        )
        return {"valid": valid, "checked": checked, "errors": errors}

    # Cleanup

    async def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup directory.  Returns ``True`` on success."""
        backup_path = self._backup_root / backup_name
        if not backup_path.exists():
            return False
        await asyncio.to_thread(shutil.rmtree, backup_path)
        self._log.info("backup_deleted", name=backup_name)
        return True

    async def prune_backups(self, *, keep: int = 10) -> list[str]:
        """Delete oldest backups, keeping the most recent *keep* snapshots."""
        all_backups = await self.list_backups()
        to_delete = all_backups[keep:]
        deleted: list[str] = []
        for b in to_delete:
            name = b.get("name", "")
            if name and await self.delete_backup(name):
                deleted.append(name)
        self._log.info("backups_pruned", kept=keep, deleted=len(deleted))
        return deleted

    # Internal helpers

    async def _run_pg_dump(self, output_path: Path, *, compression: bool = True) -> None:
        cmd: list[str | None] = [
            self._pg_dump,
            "--dbname", self._pg_conn,
            "--format=custom",
            "--file", str(output_path),
        ]
        if compression:
            cmd.append("--compress=6")

        filtered_cmd: list[str] = [x for x in cmd if x is not None]
        self._log.debug("pg_dump_start", cmd=" ".join(filtered_cmd))
        proc = await asyncio.create_subprocess_exec(
            *filtered_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise BackupError(
                f"pg_dump failed (rc={proc.returncode}): {stderr.decode().strip()}"
            )

    async def _run_pg_restore(self, dump_path: Path) -> None:
        cmd: list[str | None] = [
            self._pg_restore,
            "--dbname", self._pg_conn,
            "--clean",
            "--if-exists",
            str(dump_path),
        ]
        filtered_cmd: list[str] = [x for x in cmd if x is not None]
        self._log.debug("pg_restore_start", cmd=" ".join(filtered_cmd))
        proc = await asyncio.create_subprocess_exec(
            *filtered_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            # pg_restore returns non-zero on warnings too; log but don't always raise
            stderr_text = stderr.decode().strip()
            if "error" in stderr_text.lower():
                raise BackupError(
                    f"pg_restore failed (rc={proc.returncode}): {stderr_text}"
                )
            self._log.warning("pg_restore_warnings", warnings=stderr_text)

    @staticmethod
    def _sha256(file_path: Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(_CHUNK_SIZE)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _load_manifest(backup_path: Path) -> dict[str, Any]:
        manifest_file = backup_path / _MANIFEST_FILE
        if not manifest_file.exists():
            return {"components": {}}
        result: dict[str, Any] = json.loads(manifest_file.read_text())
        return result


__all__ = [
    "BackupError",
    "BackupManager",
]
