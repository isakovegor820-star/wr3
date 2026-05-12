# Data Retention And Deletion Policy

Status: implemented for audit records; object-storage deletion must be wired
before public paid launch.

## Tier Retention

| Tier | Retention |
| --- | --- |
| Free | 7 days |
| Hobby | 30 days |
| Team | 180 days |
| Pro | 365 days or custom agreement |

## Implemented Controls

- `AuditRecord.retention_until` is set when an audit is created.
- `scripts/retention_sweep.py` deletes expired audit records or dry-runs them.
- `wr3.retention_sweep` Celery task is available for scheduled sweeps.
- `DELETE /v1/audits/{id}` lets an owner delete a private audit record.

## Required Production Extension

When R2/object storage is configured, deletion must also remove:

- private reports
- raw engine outputs
- PoC artifacts
- fuzzer counterexamples
- prompt/response debug payloads
- backup references outside legal retention windows

## Backup Retention

Backups should be encrypted and retained for 30 days during beta unless a legal
hold applies. The backup script supports local encrypted files and optional R2
upload.

## User Deletion Request

1. Verify owner identity.
2. Delete audit record.
3. Delete artifacts.
4. Remove or anonymize operational references where feasible.
5. Confirm completion privately.
