# SEC & OJK Regulatory Compliance

## Overview

Enthropy provides automated compliance reporting for both SEC (U.S. Securities and Exchange Commission) and OJK (Otoritas Jasa Keuangan, Indonesia's Financial Services Authority) regulatory requirements. The compliance engine generates, validates, encrypts, and archives all required reports.

## SEC Compliance

### Automated Reports

| Report | Frequency | Deadline | Description |
|--------|-----------|----------|-------------|
| **13F Holdings** | Quarterly | 45 days after quarter end | Institutional holdings > $100M |
| **Form ADV** | Annual + amendments | 90 days after fiscal year | Investment advisor registration |
| **Reg SHO** | Daily | T+1 | Short sale locate and reporting |
| **CAT (Consolidated Audit Trail)** | Real-time | Intraday | Full order lifecycle tracking |
| **Form PF** | Quarterly/Annual | 60 days (large) / 120 days (small) | Private fund risk reporting |

### Implementation

```python
from enthropy.compliance.engine import ComplianceEngine

engine = ComplianceEngine()

# Generate SEC 13F Holdings Report
report = await engine.generate_sec_report(
    report_type="13F",
    quarter="2026-Q1",
    tenant_id="fund-abc",
    include_options=True,
)

# Report object contains:
# - report.data: structured holdings data
# - report.xml: SEC EDGAR XML format
# - report.hash: SHA-256 integrity hash
# - report.generated_at: timestamp
# - report.filing_deadline: calculated deadline

# Export for filing
await engine.export_report(
    report=report,
    format="edgar_xml",
    output_path="reports/13F_2026_Q1.xml",
    encrypt=True,
)
```

### CAT Reporting

The Consolidated Audit Trail requires real-time tracking of the full order lifecycle:

```python
# CAT events are generated automatically from order flow
# Each order state transition creates a CAT-compliant event:
#   - Order Origination (new order received)
#   - Order Route (sent to exchange)
#   - Order Accepted (exchange acknowledgment)
#   - Order Modified (price/qty change)
#   - Order Fill (partial or full)
#   - Order Cancel (client or exchange initiated)

# Query CAT events for audit
events = await engine.get_cat_events(
    order_id="550e8400-e29b-41d4-a716-446655440000",
    include_timestamps=True,
)
```

## OJK (Otoritas Jasa Keuangan) Compliance

### Requirements

| Report | Frequency | Description |
|--------|-----------|-------------|
| **Daily Transaction Report** | Daily (T+1) | All trades on IDX-listed securities |
| **Monthly Portfolio Composition** | Monthly | Holdings and NAV breakdown |
| **Risk Management Report** | Quarterly | VaR, stress test results, limit utilization |
| **AML Transaction Monitoring** | Real-time | Suspicious activity detection and reporting |
| **MKBD Report** | Monthly | Minimum capital adequacy (Modal Kerja Bersih Disesuaikan) |
| **Annual Compliance Report** | Annual | Comprehensive compliance status |

### Implementation

```python
# Generate OJK Daily Transaction Report
report = await engine.generate_ojk_report(
    report_type="daily_transaction",
    date="2026-03-06",
    tenant_id="idx-client",
)

# Generate Monthly Portfolio Report
portfolio_report = await engine.generate_ojk_report(
    report_type="monthly_portfolio",
    month="2026-03",
    tenant_id="idx-client",
    include_nav=True,
    include_concentration=True,
)

# Generate Risk Management Report
risk_report = await engine.generate_ojk_report(
    report_type="quarterly_risk",
    quarter="2026-Q1",
    tenant_id="idx-client",
    include_var=True,
    include_stress_test=True,
)
```

### AML Transaction Monitoring

Enthropy integrates real-time AML monitoring for OJK compliance:

```python
# AML rules are applied to every transaction
aml_result = await engine.check_aml(
    transaction={
        "type": "trade",
        "symbol": "BBCA.JK",
        "side": "buy",
        "quantity": "100000",
        "notional": "920000000",  # IDR
        "client_id": "CLI-12345",
    },
)

# If suspicious activity detected:
if aml_result.flagged:
    # Automatically generates Suspicious Transaction Report (LTKM)
    await engine.file_suspicious_report(
        transaction_id=aml_result.transaction_id,
        risk_score=aml_result.risk_score,
        indicators=aml_result.indicators,
    )
```

**AML Detection Rules:**
- Transaction amount > IDR 500M (single transaction threshold)
- Cumulative daily volume > IDR 1B (aggregation threshold)
- Pattern detection: structuring, layering, rapid account turnover
- Sanctions list screening (OFAC, UN, Indonesia PPATK)

## Audit Trail

All compliance exports follow a strict integrity chain:

1. **Generation**: Report data assembled from audited database records
2. **Validation**: Business rule validation (completeness, accuracy)
3. **Encryption**: AES-256-GCM encryption with compliance-specific derived key
4. **Signing**: SHA-256 hash computed over encrypted payload for integrity verification
5. **Archival**: Encrypted report stored in S3 with versioning (see `infra/terraform/main.tf`)
6. **Logging**: Full audit trail entry with metadata

```python
# Verify report integrity
is_valid = await engine.verify_report_integrity(
    report_path="s3://enthropy-backups/compliance/13F_2026_Q1.enc",
    expected_hash="sha256:abc123...",
)
```

### Audit Log Schema

Every compliance action is recorded in `audit.logs`:

```json
{
  "event_type": "compliance_export",
  "entity_type": "sec_13f_report",
  "entity_id": "RPT-2026-Q1-001",
  "actor": "compliance_bot@enthropy.dev",
  "action": "generate_and_export",
  "details": {
    "report_type": "13F",
    "quarter": "2026-Q1",
    "tenant_id": "fund-abc",
    "holdings_count": 47,
    "total_value": "2500000000.00",
    "output_format": "edgar_xml",
    "encrypted": true,
    "sha256_hash": "abc123..."
  },
  "ip_address": "10.0.1.100",
  "timestamp": "2026-04-15T08:00:00Z"
}
```

## Export Formats

| Format | Use Case | Description |
|--------|----------|-------------|
| JSON | Machine-readable | Structured data for API consumers |
| CSV | Spreadsheet | Compatible with Excel/Google Sheets |
| PDF | Human-readable | Formatted reports via reporting service |
| EDGAR XML | SEC filing | SEC EDGAR submission format |
| XBRL | Regulatory | Extensible Business Reporting Language |

## Scheduling

Compliance reports can be scheduled via the admin API or cron configuration:

```yaml
# Example cron schedule for automated compliance
compliance_schedules:
  ojk_daily_transaction:
    cron: "0 6 * * 1-5"  # 6 AM WIB, weekdays
    report_type: "daily_transaction"
    auto_submit: false    # Require manual review before submission

  sec_13f:
    cron: "0 8 15 1,4,7,10 *"  # 15th of quarter-end months
    report_type: "13F"
    auto_submit: false

  aml_monitoring:
    cron: "*/5 * * * *"   # Every 5 minutes
    report_type: "aml_scan"
    auto_submit: true     # Immediate flagging
```

## Monitoring & Alerts

Compliance-related alerts are configured in the monitoring stack (see `infra/monitoring/alerts.yaml`):

- **report_generation_failure**: Alert if scheduled report fails to generate
- **aml_suspicious_activity**: Immediate alert on flagged transactions
- **compliance_deadline_approaching**: Warning 7 days before filing deadline
- **audit_log_gap**: Alert if audit logging has gaps

## Related Documentation

- [UU PDP Compliance Guide](uu_pdp_guide.md) - Data privacy and encryption
- [Architecture Overview](../architecture/overview.md) - System design and audit trail
- [Risk Engine Tests](../../tests/unit/test_risk_limits.py) - Risk limit validation
- [Prometheus Alerts](../../infra/monitoring/alerts.yaml) - Monitoring configuration
- [Database Schema](../../scripts/setup_db.py) - Audit log table DDL
