from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from wr3_api.domain.schemas import AuditEvent, utc_now
from wr3_api.services.repository import AuditRepository


@dataclass(frozen=True)
class RetentionDecision:
    audit_id: str
    action: str
    reason: str
    retention_until: str | None = None


@dataclass(frozen=True)
class RetentionRunResult:
    checked: int
    deleted: int
    retained: int
    decisions: list[RetentionDecision] = field(default_factory=list)


class RetentionService:
    """Tier-retention enforcement boundary.

    The service intentionally deletes only audit records through the repository.
    Production R2/KMS artifact deletion is a separate adapter and must be wired
    before paid launch.
    """

    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    def run_once(self, *, now: datetime | None = None, dry_run: bool = False) -> RetentionRunResult:
        now = now or utc_now()
        decisions: list[RetentionDecision] = []
        deleted = 0
        retained = 0
        records = self._repository.list_records()
        for record in records:
            if record.retention_until is None:
                retained += 1
                decisions.append(
                    RetentionDecision(
                        audit_id=str(record.audit_id),
                        action="retain",
                        reason="retention_until_missing_legacy_record",
                    )
                )
                continue
            if record.retention_until > now:
                retained += 1
                decisions.append(
                    RetentionDecision(
                        audit_id=str(record.audit_id),
                        action="retain",
                        reason="retention_window_active",
                        retention_until=record.retention_until.isoformat(),
                    )
                )
                continue
            decisions.append(
                RetentionDecision(
                    audit_id=str(record.audit_id),
                    action="delete" if not dry_run else "would_delete",
                    reason="tier_retention_expired",
                    retention_until=record.retention_until.isoformat(),
                )
            )
            if not dry_run and self._repository.delete(record.audit_id):
                deleted += 1
            else:
                retained += 1 if dry_run else 0
            if dry_run:
                record.events.append(
                    AuditEvent(
                        audit_id=record.audit_id,
                        event_type="retention_dry_run",
                        payload={"retention_until": record.retention_until.isoformat()},
                    )
                )
                self._repository.save(record)
        return RetentionRunResult(
            checked=len(records),
            deleted=deleted,
            retained=retained,
            decisions=decisions,
        )
