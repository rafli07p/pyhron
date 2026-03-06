# SEC & OJK Regulatory Compliance

## Overview

Enthropy provides automated compliance reporting for both SEC (US) and OJK (Indonesia) regulatory requirements.

## SEC Compliance

### Automated Reports
- **13F Holdings Report**: Quarterly filing of institutional holdings
- **Form ADV**: Advisor registration updates
- **Reg SHO**: Short sale reporting
- **CAT (Consolidated Audit Trail)**: Order lifecycle tracking

### Implementation
```python
from services.risk.compliance import ComplianceEngine

engine = ComplianceEngine()
report = await engine.generate_sec_report(
    report_type="13F",
    quarter="2026-Q1",
    tenant_id="fund-abc"
)
```

## OJK (Otoritas Jasa Keuangan) Compliance

### Requirements
- Daily transaction reporting for IDX-listed securities
- Monthly portfolio composition reports
- Risk management framework documentation
- Anti-money laundering (AML) transaction monitoring

### Implementation
```python
report = await engine.generate_ojk_report(
    report_type="daily_transaction",
    date="2026-03-06",
    tenant_id="idx-client"
)
```

## Audit Trail

All compliance exports are:
1. **Encrypted** using AES-256 (Fernet)
2. **Signed** with SHA-256 hash for integrity verification
3. **Logged** in the audit trail with full metadata
4. **Stored** in encrypted backup with configurable retention

## Export Formats
- JSON (machine-readable)
- CSV (spreadsheet-compatible)
- PDF (human-readable, via reporting service)
