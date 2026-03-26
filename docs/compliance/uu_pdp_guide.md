# UU PDP (Undang-Undang Pelindungan Data Pribadi) Compliance Guide

## Overview

Indonesia's Personal Data Protection Law (UU PDP, Law No. 27/2022) establishes comprehensive data privacy requirements that apply to any entity processing personal data of Indonesian citizens. Pyhron implements technical and organizational controls to ensure full compliance.

This guide covers the platform's data protection architecture, encryption implementation, audit trail mechanisms, and data retention policies.

## Regulatory Requirements Summary

| Requirement | UU PDP Article | Pyhron Implementation |
|-------------|---------------|------------------------|
| Lawful processing | Art. 20 | Consent tracking, purpose limitation |
| Data minimization | Art. 16(d) | Field-level access control |
| Storage limitation | Art. 16(e) | Automated retention policies |
| Integrity & confidentiality | Art. 16(f) | AES-256-GCM encryption |
| Right to access | Art. 7 | Data export API |
| Right to erasure | Art. 8 | Tenant data purge |
| Breach notification | Art. 46 | Automated alerting pipeline |
| Cross-border transfer | Art. 56 | Data residency controls (Jakarta region) |

## Data Classification

| Category | Examples | Classification | Protection Level |
|----------|----------|---------------|-----------------|
| Personal Data (PII) | Name (nama), NIK, email, phone | High | AES-256-GCM encrypted at rest + in transit |
| Financial Data | Account balances, trade history | High | Encrypted + access-controlled + audit logged |
| Strategy IP | Alpha models, signals, parameters | Critical | Encrypted with tenant-specific derived keys |
| Market Data | Prices, volumes, OHLCV | Standard | Standard protection, public data |
| System Data | Logs, metrics, config | Low | Retention-controlled, PII-scrubbed |

## Technical Controls

### Encryption Architecture

Pyhron uses AES-256-GCM (Galois/Counter Mode) for authenticated encryption, providing both confidentiality and integrity verification.

**Key hierarchy:**
```
Master Key (256-bit, from HSM/KMS)
  ├── User PII Key (derived via HKDF, context: "user_pii")
  ├── Trading Data Key (derived via HKDF, context: "trading_data")
  ├── Strategy IP Key (derived via HKDF, context: "strategy_ip")
  └── Audit Key (derived via HKDF, context: "audit_data")
```

**Implementation:** See `src/pyhron/shared/encryption/service.py`

```python
from pyhron.shared.encryption.service import EncryptionService, FieldEncryptor

# Field-level encryption for PII
encryptor = FieldEncryptor(encryption_service)
encrypted_record = encryptor.encrypt_fields(
    record={"name": "Budi Santoso", "nik": "3201012345678901", "balance": "50000000"},
    fields=["name", "nik"],  # Only PII fields encrypted
)
```

**Key properties:**
- Each encryption operation uses a unique nonce (no nonce reuse)
- GCM authentication tag detects any tampering
- Key rotation supported without data re-encryption downtime
- Derived keys are context-specific (compromise of one does not expose others)

**Validation:** See `tests/unit/test_encryption.py` for comprehensive tests including tamper detection, key rotation, and compliance checks.

### Access Control (RBAC)

Role-based access control enforces the principle of least privilege:

| Role | Market Data | Orders | Portfolio | Risk | Admin | Compliance |
|------|------------|--------|-----------|------|-------|-----------|
| VIEWER | Read | - | Read own | Read | - | - |
| ANALYST | Read | - | Read own | Read | - | - |
| TRADER | Read | Create/Cancel | Read/Write | Read | - | - |
| RISK_MANAGER | Read | Cancel | Read all | Read/Write | - | Read |
| ADMIN | Full | Full | Full | Full | Full | Full |

Multi-tenancy is enforced at the database query level via `tenant_id` on all data models, preventing cross-tenant data access.

### Audit Trail

Every data mutation and sensitive operation is logged to the immutable `audit.logs` table:

```sql
-- Audit log entry structure
{
  "event_type": "data_access",
  "entity_type": "user_pii",
  "entity_id": "USR-12345",
  "actor": "trader@pyhron.dev",
  "action": "decrypt_field",
  "details": {
    "fields": ["name", "nik"],
    "purpose": "compliance_report",
    "justification": "OJK quarterly filing"
  },
  "ip_address": "10.0.1.50",
  "timestamp": "2024-01-15T09:30:00Z"
}
```

Audit log guarantees:
- Append-only (no updates or deletes)
- Encrypted backup to S3 (see `infra/terraform/main.tf` for bucket config)
- Retention: 7 years (per OJK requirements)
- Exportable in JSON/CSV for regulatory review

### Data Retention Policies

| Data Category | Active Retention | Archive | Purge |
|--------------|-----------------|---------|-------|
| Trade records | 5 years | Glacier (5+ years) | 10 years |
| Market data (ticks) | 2 years | Glacier (2+ years) | 7 years |
| User PII | Account lifetime | - | On account deletion |
| Audit logs | 7 years | Glacier (7+ years) | Never (regulatory) |
| Backtest results | 1 year | Glacier (1+ years) | 3 years |

Automated lifecycle management via:
- PostgreSQL partitioning for time-series data (monthly partitions)
- S3 lifecycle rules (see `infra/terraform/main.tf` for S3 bucket lifecycle)
- Retention enforcement via daily cron job

### Data Residency

For Indonesian data subjects, Pyhron supports data residency in the Jakarta region (ap-southeast-3):

- Primary data store: ap-southeast-1 (Singapore)
- Jakarta replica: ap-southeast-3 for PII of Indonesian citizens
- Cross-border transfer logging for compliance audits
- See `infra/terraform/main.tf` for Jakarta region VPC and storage configuration

## Data Subject Rights Implementation

### Right to Access (Art. 7)

```python
# Export all data for a user
from pyhron.compliance.data_subject import DataSubjectService

service = DataSubjectService()
export = await service.export_user_data(
    user_id="USR-12345",
    format="json",  # or "csv"
    include_audit_trail=True,
)
```

### Right to Rectification (Art. 8)

User personal data can be updated via the admin API. All changes are audit-logged with before/after values.

### Right to Erasure (Art. 8)

```python
# Purge all PII for a user (preserves anonymized trade records)
await service.purge_user_data(
    user_id="USR-12345",
    retain_anonymized_trades=True,
    reason="user_request",
)
```

### Right to Data Portability (Art. 13)

Data exports available in JSON and CSV formats via the admin API endpoint `/admin/compliance/export`.

## Compliance Reporting

Automated compliance reports generated via `src/pyhron/compliance/`:

| Report | Frequency | Format | Description |
|--------|-----------|--------|-------------|
| Data processing activities | Quarterly | PDF/JSON | ROPA (Record of Processing Activities) |
| Data breach log | On event | JSON | Incident details, impact assessment |
| Cross-border transfer log | Monthly | CSV | All data transfers outside Indonesia |
| Access audit summary | Monthly | PDF | Who accessed what PII and why |

## Incident Response

In case of a data breach (per UU PDP Art. 46):

1. **Detection**: Automated monitoring alerts (see `infra/monitoring/alerts.yaml`)
2. **Assessment**: Within 24 hours - determine scope and impact
3. **Notification**: Within 72 hours - notify data subjects and authorities
4. **Remediation**: Contain breach, rotate keys, patch vulnerability
5. **Documentation**: Full incident report with timeline and actions taken

## Related Documentation

- [Encryption Service Tests](../../tests/unit/test_encryption.py) - Test coverage for all encryption operations
- [SEC/OJK Reporting](sec_ojk_reporting.md) - Regulatory reporting automation
- [Database Setup](../../scripts/setup_db.py) - Schema including audit tables
- [Architecture Overview](../architecture/overview.md) - System design and data flow
