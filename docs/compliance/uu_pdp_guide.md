# UU PDP (Undang-Undang Pelindungan Data Pribadi) Compliance Guide

## Overview

Indonesia's Personal Data Protection Law (UU PDP, Law No. 27/2022) establishes comprehensive data privacy requirements. Enthropy implements the following controls to ensure compliance.

## Data Classification

| Category | Examples | Protection Level |
|----------|----------|-----------------|
| Personal Data | Name, email, phone | Encrypted at rest |
| Financial Data | Account balances, trades | Encrypted + audit logged |
| Strategy IP | Alpha models, signals | AES-256 encrypted |
| Market Data | Prices, volumes | Standard protection |

## Technical Controls

### Encryption
- **At rest**: AES-256 via `data-platform/encryption/` (Fernet)
- **In transit**: TLS 1.3 enforced on all API endpoints
- **Strategy IP**: Alpha models encrypted with tenant-specific keys

### Access Control
- **RBAC**: Role-based access (ADMIN, TRADER, ANALYST, VIEWER) via `shared/security/rbac/`
- **Multi-tenancy**: Tenant isolation via `tenant_id` on all data models
- **JWT Authentication**: Token-based auth with configurable expiry

### Audit Trail
- Every data mutation is logged via `shared/security/audit/`
- Audit logs include: user, action, resource, timestamp, IP address, tenant_id
- Export to JSON/CSV for regulatory review

### Data Retention
- Configure retention periods per data category
- Automated backup and purge via `data-platform/backup/`
- Right to deletion: user data can be purged per tenant

## Compliance Reporting

Use `services/risk/compliance/` to generate:
- Data processing activity reports
- Data breach notifications
- Cross-border transfer documentation
- Annual compliance summaries

## Data Subject Rights

Enthropy supports:
1. **Right to access**: Export user data via admin API
2. **Right to rectification**: Update personal data via user management
3. **Right to erasure**: Tenant data purge functionality
4. **Right to data portability**: JSON/CSV export
