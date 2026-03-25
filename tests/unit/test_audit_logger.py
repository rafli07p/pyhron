"""Unit tests for shared.security.audit — AuditLogger, AuditRecord, export."""

from __future__ import annotations

import csv
import io
import json

import pytest

from shared.security.audit import (
    AuditAction,
    AuditLogger,
    AuditRecord,
    ExportFormat,
)

# =============================================================================
# AuditRecord
# =============================================================================


class TestAuditRecord:
    def test_creation(self) -> None:
        record = AuditRecord(
            user_id="u-1",
            tenant_id="t-1",
            action=AuditAction.CREATE,
            resource="order/ord-1",
        )
        assert record.user_id == "u-1"
        assert record.tenant_id == "t-1"
        assert record.action == AuditAction.CREATE
        assert record.success is True
        assert record.record_id  # Non-empty UUID

    def test_to_dict(self) -> None:
        record = AuditRecord(
            user_id="u-1",
            tenant_id="t-1",
            action="CREATE",
            resource="order/ord-1",
            details={"symbol": "BBCA"},
        )
        d = record.to_dict()
        assert d["user_id"] == "u-1"
        assert d["details"]["symbol"] == "BBCA"
        assert "timestamp" in d
        assert "record_id" in d

    def test_repr(self) -> None:
        record = AuditRecord(
            user_id="u-1",
            tenant_id="t-1",
            action="READ",
            resource="portfolio/p-1",
        )
        r = repr(record)
        assert "AuditRecord" in r
        assert "u-1" in r


# =============================================================================
# AuditLogger
# =============================================================================


class TestAuditLogger:
    def test_log_action_creates_record(self) -> None:
        logger = AuditLogger(service="test-svc")
        record = logger.log_action(
            user_id="u-1",
            action=AuditAction.ORDER_SUBMIT,
            resource="order/ord-1",
            tenant_id="t-1",
        )
        assert record.service == "test-svc"
        assert record.action == AuditAction.ORDER_SUBMIT

    def test_record_count(self) -> None:
        logger = AuditLogger()
        assert logger.record_count == 0
        logger.log_action(user_id="u-1", action="CREATE", resource="r-1")
        logger.log_action(user_id="u-2", action="DELETE", resource="r-2")
        assert logger.record_count == 2

    def test_get_records_filter_by_user(self) -> None:
        logger = AuditLogger()
        logger.log_action(user_id="alice", action="CREATE", resource="r-1")
        logger.log_action(user_id="bob", action="CREATE", resource="r-2")
        logger.log_action(user_id="alice", action="DELETE", resource="r-3")

        records = logger.get_records(user_id="alice")
        assert len(records) == 2
        assert all(r.user_id == "alice" for r in records)

    def test_get_records_filter_by_action(self) -> None:
        logger = AuditLogger()
        logger.log_action(user_id="u-1", action="CREATE", resource="r-1")
        logger.log_action(user_id="u-1", action="DELETE", resource="r-2")

        records = logger.get_records(action="DELETE")
        assert len(records) == 1

    def test_get_records_limit(self) -> None:
        logger = AuditLogger()
        for i in range(10):
            logger.log_action(user_id="u-1", action="READ", resource=f"r-{i}")

        records = logger.get_records(limit=3)
        assert len(records) == 3

    def test_clear(self) -> None:
        logger = AuditLogger()
        logger.log_action(user_id="u-1", action="CREATE", resource="r-1")
        count = logger.clear()
        assert count == 1
        assert logger.record_count == 0

    def test_buffer_eviction(self) -> None:
        logger = AuditLogger(buffer_size=5)
        for i in range(10):
            logger.log_action(user_id="u-1", action="CREATE", resource=f"r-{i}")
        assert logger.record_count == 5

    def test_on_record_callback(self) -> None:
        captured: list[AuditRecord] = []
        logger = AuditLogger(on_record=captured.append)
        logger.log_action(user_id="u-1", action="CREATE", resource="r-1")
        assert len(captured) == 1

    def test_on_record_callback_error_handled(self) -> None:
        def bad_callback(record: AuditRecord) -> None:
            raise RuntimeError("oops")

        logger = AuditLogger(on_record=bad_callback)
        # Should not raise
        logger.log_action(user_id="u-1", action="CREATE", resource="r-1")
        assert logger.record_count == 1


# =============================================================================
# Export
# =============================================================================


class TestExport:
    def test_export_json(self) -> None:
        logger = AuditLogger()
        logger.log_action(user_id="u-1", action="CREATE", resource="r-1", details={"k": "v"})
        raw = logger.export_audit_log(format="json")
        data = json.loads(raw)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["user_id"] == "u-1"

    def test_export_csv(self) -> None:
        logger = AuditLogger()
        logger.log_action(user_id="u-1", action="CREATE", resource="r-1")
        raw = logger.export_audit_log(format="csv")
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["user_id"] == "u-1"

    def test_export_invalid_format_raises(self) -> None:
        logger = AuditLogger()
        with pytest.raises(ValueError):
            logger.export_audit_log(format="xml")


# =============================================================================
# Enumerations
# =============================================================================


def test_audit_action_values() -> None:
    assert AuditAction.CREATE == "CREATE"
    assert AuditAction.LOGIN_FAILED == "LOGIN_FAILED"
    assert AuditAction.ORDER_SUBMIT == "ORDER_SUBMIT"


def test_export_format_values() -> None:
    assert ExportFormat.JSON == "json"
    assert ExportFormat.CSV == "csv"
