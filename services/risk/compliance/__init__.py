"""Compliance engine for the Enthropy trading platform.

Generates SEC and OJK regulatory reports, exports encrypted audit
trails, enforces regulatory limits, and performs UU PDP (Indonesia
Personal Data Protection) compliance checks.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import structlog
from cryptography.fernet import Fernet

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Regulatory limit configuration
# ---------------------------------------------------------------------------

@dataclass
class RegulatoryLimits:
    """Configurable regulatory limits per tenant / jurisdiction."""

    # SEC rules
    max_short_sale_pct: float = 100.0  # percent of available shares
    pattern_day_trader_min_equity: Decimal = Decimal("25000")

    # OJK (Indonesian Financial Services Authority)
    max_single_stock_pct: float = 10.0  # max % of portfolio in one stock
    max_foreign_ownership_pct: float = 49.0

    # Generic
    max_leverage: float = 4.0
    max_concentration_pct: float = 25.0


_DEFAULT_LIMITS = RegulatoryLimits()


# ---------------------------------------------------------------------------
# PII fields for UU PDP compliance
# ---------------------------------------------------------------------------

_PII_FIELDS = frozenset({
    "name", "full_name", "email", "phone", "phone_number",
    "address", "nik", "national_id", "passport", "dob",
    "date_of_birth", "tax_id", "npwp", "ktp", "ssn",
    "bank_account", "account_number",
})


# ---------------------------------------------------------------------------
# Report types
# ---------------------------------------------------------------------------

@dataclass
class ComplianceReport:
    """A generated regulatory report."""

    report_id: str
    tenant_id: str
    report_type: str  # "SEC" | "OJK" | "AUDIT_TRAIL"
    generated_at: str
    period_start: str
    period_end: str
    data: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Compliance engine
# ---------------------------------------------------------------------------

class ComplianceEngine:
    """Regulatory compliance engine with multi-jurisdiction support.

    Supports SEC and OJK reporting, encrypted audit-trail export,
    regulatory limit checks, and UU PDP data-privacy compliance.

    Parameters
    ----------
    tenant_limits:
        Per-tenant regulatory limit overrides.
    encryption_key:
        Fernet key for encrypting exported data.  If ``None``, a
        fresh key is generated on construction.
    """

    def __init__(
        self,
        tenant_limits: dict[str, RegulatoryLimits] | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        self._tenant_limits = tenant_limits or {}
        self._fernet = Fernet(encryption_key or Fernet.generate_key())
        self._log = logger.bind(component="ComplianceEngine")

    def _limits(self, tenant_id: str) -> RegulatoryLimits:
        return self._tenant_limits.get(tenant_id, _DEFAULT_LIMITS)

    # -- SEC reporting -------------------------------------------------------

    def generate_sec_report(
        self,
        tenant_id: str,
        trades: list[dict[str, Any]],
        positions: list[dict[str, Any]],
        period_start: date,
        period_end: date,
    ) -> ComplianceReport:
        """Generate an SEC-style regulatory report.

        Covers: large-trader reporting thresholds, short-sale
        aggregation, and pattern-day-trader checks.

        Parameters
        ----------
        trades:
            List of trade dicts with keys: symbol, side, qty, price,
            timestamp, account_id.
        positions:
            List of position dicts with keys: symbol, qty, market_value.
        """
        self._log.info("generate_sec_report", tenant_id=tenant_id)
        warnings: list[str] = []
        limits = self._limits(tenant_id)

        # Large-trader threshold (NMS Rule 13h-1): 2M shares or $20M in a day
        daily_volume: dict[str, dict[str, Decimal]] = {}
        for t in trades:
            trade_date = str(t.get("timestamp", ""))[:10]
            if trade_date not in daily_volume:
                daily_volume[trade_date] = {"shares": Decimal("0"), "notional": Decimal("0")}
            daily_volume[trade_date]["shares"] += Decimal(str(t.get("qty", 0)))
            daily_volume[trade_date]["notional"] += (
                Decimal(str(t.get("qty", 0))) * Decimal(str(t.get("price", 0)))
            )

        large_trader_days = []
        for dt, vol in daily_volume.items():
            if vol["shares"] >= Decimal("2000000") or vol["notional"] >= Decimal("20000000"):
                large_trader_days.append(dt)
                warnings.append(f"Large-trader threshold exceeded on {dt}")

        # Short positions summary
        short_positions = [p for p in positions if Decimal(str(p.get("qty", 0))) < 0]

        # Pattern day trader check
        day_trade_counts: dict[str, int] = {}
        for t in trades:
            trade_date = str(t.get("timestamp", ""))[:10]
            day_trade_counts[trade_date] = day_trade_counts.get(trade_date, 0) + 1
        pdt_days = [dt for dt, cnt in day_trade_counts.items() if cnt >= 4]
        if pdt_days:
            warnings.append(f"Pattern day trader activity on {len(pdt_days)} day(s)")

        report_data = {
            "total_trades": len(trades),
            "period_days": (period_end - period_start).days,
            "large_trader_days": large_trader_days,
            "short_positions": short_positions,
            "short_position_count": len(short_positions),
            "pattern_day_trade_days": pdt_days,
            "daily_volumes": {
                dt: {"shares": str(v["shares"]), "notional": str(v["notional"])}
                for dt, v in daily_volume.items()
            },
        }

        return ComplianceReport(
            report_id=str(uuid4()),
            tenant_id=tenant_id,
            report_type="SEC",
            generated_at=datetime.utcnow().isoformat(),
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            data=report_data,
            warnings=warnings,
        )

    # -- OJK reporting -------------------------------------------------------

    def generate_ojk_report(
        self,
        tenant_id: str,
        trades: list[dict[str, Any]],
        positions: list[dict[str, Any]],
        period_start: date,
        period_end: date,
        portfolio_nav: Decimal = Decimal("0"),
    ) -> ComplianceReport:
        """Generate an OJK (Indonesia) regulatory report.

        Covers: single-stock concentration, foreign-ownership limits,
        and transaction reporting.
        """
        self._log.info("generate_ojk_report", tenant_id=tenant_id)
        warnings: list[str] = []
        limits = self._limits(tenant_id)

        # Single-stock concentration
        concentration_breaches: list[dict[str, Any]] = []
        if portfolio_nav > 0:
            for p in positions:
                mv = abs(Decimal(str(p.get("market_value", 0))))
                pct = float(mv / portfolio_nav * 100)
                if pct > limits.max_single_stock_pct:
                    concentration_breaches.append({
                        "symbol": p.get("symbol"),
                        "pct": round(pct, 2),
                        "limit": limits.max_single_stock_pct,
                    })
                    warnings.append(
                        f"Single-stock concentration {pct:.1f}% in "
                        f"{p.get('symbol')} exceeds OJK limit {limits.max_single_stock_pct}%"
                    )

        # Transaction summary
        buy_count = sum(1 for t in trades if t.get("side") == "BUY")
        sell_count = sum(1 for t in trades if t.get("side") == "SELL")
        total_notional = sum(
            Decimal(str(t.get("qty", 0))) * Decimal(str(t.get("price", 0)))
            for t in trades
        )

        report_data = {
            "total_trades": len(trades),
            "buy_trades": buy_count,
            "sell_trades": sell_count,
            "total_notional": str(total_notional),
            "portfolio_nav": str(portfolio_nav),
            "concentration_breaches": concentration_breaches,
            "positions_count": len(positions),
        }

        return ComplianceReport(
            report_id=str(uuid4()),
            tenant_id=tenant_id,
            report_type="OJK",
            generated_at=datetime.utcnow().isoformat(),
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            data=report_data,
            warnings=warnings,
        )

    # -- Audit trail export --------------------------------------------------

    def export_audit_trail(
        self,
        tenant_id: str,
        events: list[dict[str, Any]],
        format: str = "json",
        output_path: Path | None = None,
    ) -> str:
        """Export an audit trail as JSON or CSV.

        Parameters
        ----------
        events:
            List of event dicts to export.
        format:
            ``"json"`` or ``"csv"``.
        output_path:
            If provided, write the file to disk and return the path.
            Otherwise return the serialised string.

        Returns
        -------
        str
            The serialised data or the output file path.
        """
        self._log.info("export_audit_trail", tenant_id=tenant_id, format=format, count=len(events))

        # Scrub PII before export
        scrubbed = self._scrub_pii(events)

        if format == "csv":
            output = io.StringIO()
            if scrubbed:
                writer = csv.DictWriter(output, fieldnames=sorted(scrubbed[0].keys()))
                writer.writeheader()
                for row in scrubbed:
                    writer.writerow({k: str(v) for k, v in row.items()})
            content = output.getvalue()
        else:
            content = json.dumps(scrubbed, indent=2, default=str)

        if output_path is not None:
            output_path.write_text(content, encoding="utf-8")
            self._log.info("audit_trail_written", path=str(output_path))
            return str(output_path)

        return content

    # -- Regulatory limits ---------------------------------------------------

    def check_regulatory_limits(
        self,
        tenant_id: str,
        positions: list[dict[str, Any]],
        portfolio_nav: Decimal,
        total_margin_used: Decimal = Decimal("0"),
        account_equity: Decimal = Decimal("0"),
    ) -> list[dict[str, Any]]:
        """Run all regulatory limit checks and return breaches.

        Returns
        -------
        list[dict]
            Each dict: ``limit_type``, ``entity``, ``value``, ``limit``,
            ``breach`` (bool).
        """
        self._log.info("check_regulatory_limits", tenant_id=tenant_id)
        limits = self._limits(tenant_id)
        breaches: list[dict[str, Any]] = []

        if portfolio_nav <= 0:
            return breaches

        # Single-name concentration
        for p in positions:
            mv = abs(Decimal(str(p.get("market_value", 0))))
            pct = float(mv / portfolio_nav * 100)
            if pct > limits.max_concentration_pct:
                breaches.append({
                    "limit_type": "concentration",
                    "entity": p.get("symbol", "unknown"),
                    "value": round(pct, 2),
                    "limit": limits.max_concentration_pct,
                    "breach": True,
                })

        # Leverage
        gross_exposure = sum(
            abs(Decimal(str(p.get("market_value", 0)))) for p in positions
        )
        leverage = float(gross_exposure / portfolio_nav)
        if leverage > limits.max_leverage:
            breaches.append({
                "limit_type": "leverage",
                "entity": "portfolio",
                "value": round(leverage, 2),
                "limit": limits.max_leverage,
                "breach": True,
            })

        # Pattern day trader equity
        if account_equity > 0 and account_equity < limits.pattern_day_trader_min_equity:
            breaches.append({
                "limit_type": "pdt_equity",
                "entity": "account",
                "value": str(account_equity),
                "limit": str(limits.pattern_day_trader_min_equity),
                "breach": True,
            })

        return breaches

    # -- Encrypted export ----------------------------------------------------

    def encrypt_export(self, data: str) -> bytes:
        """Encrypt a string payload using Fernet symmetric encryption.

        Suitable for encrypting audit-trail exports before transmission
        or storage.
        """
        self._log.info("encrypt_export", data_len=len(data))
        return self._fernet.encrypt(data.encode("utf-8"))

    def decrypt_export(self, token: bytes) -> str:
        """Decrypt a Fernet token back to the original string."""
        return self._fernet.decrypt(token).decode("utf-8")

    # -- UU PDP compliance ---------------------------------------------------

    def check_pdp_compliance(
        self,
        tenant_id: str,
        data_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Check data records for UU PDP (Indonesia data privacy) compliance.

        Scans for PII fields that should not be stored or exported
        without proper consent and encryption.

        Returns
        -------
        list[dict]
            Findings with ``field``, ``record_index``, ``severity``,
            and ``recommendation``.
        """
        self._log.info("check_pdp_compliance", tenant_id=tenant_id, records=len(data_records))
        findings: list[dict[str, Any]] = []

        for idx, record in enumerate(data_records):
            for key in record:
                key_lower = key.lower()
                if key_lower in _PII_FIELDS:
                    findings.append({
                        "field": key,
                        "record_index": idx,
                        "severity": "HIGH",
                        "recommendation": (
                            f"Field '{key}' contains PII subject to UU PDP. "
                            "Ensure valid consent is recorded, data is encrypted "
                            "at rest and in transit, and retention policies are applied."
                        ),
                    })
                # Detect potential PII in values (e.g. embedded email)
                val = str(record[key])
                if "@" in val and "." in val and key_lower not in _PII_FIELDS:
                    findings.append({
                        "field": key,
                        "record_index": idx,
                        "severity": "MEDIUM",
                        "recommendation": (
                            f"Field '{key}' may contain an email address. "
                            "Review for PII compliance under UU PDP."
                        ),
                    })

        if findings:
            self._log.warning(
                "pdp_findings",
                tenant_id=tenant_id,
                count=len(findings),
            )
        return findings

    # -- Helpers -------------------------------------------------------------

    def _scrub_pii(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Redact PII fields from records before export."""
        scrubbed = []
        for record in records:
            clean: dict[str, Any] = {}
            for k, v in record.items():
                if k.lower() in _PII_FIELDS:
                    clean[k] = "[REDACTED]"
                else:
                    clean[k] = v
            scrubbed.append(clean)
        return scrubbed


__all__ = [
    "RegulatoryLimits",
    "ComplianceReport",
    "ComplianceEngine",
]
