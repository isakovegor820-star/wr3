from datetime import timedelta

from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import AuditRecord, CreateAuditRequest, utc_now
from wr3_api.services.repository import InMemoryAuditRepository
from wr3_api.services.retention import RetentionService


def test_retention_service_deletes_expired_records_and_keeps_active_records():
    repository = InMemoryAuditRepository()
    expired = AuditRecord(
        request=CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
        ),
        retention_until=utc_now() - timedelta(seconds=1),
    )
    active = AuditRecord(
        request=CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000001",
        ),
        retention_until=utc_now() + timedelta(days=1),
    )
    repository.save(expired)
    repository.save(active)

    result = RetentionService(repository).run_once()

    assert result.checked == 2
    assert result.deleted == 1
    assert repository.get(expired.audit_id) is None
    assert repository.get(active.audit_id) is not None


def test_retention_dry_run_records_event_without_delete():
    repository = InMemoryAuditRepository()
    expired = AuditRecord(
        request=CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
        ),
        retention_until=utc_now() - timedelta(seconds=1),
    )
    repository.save(expired)

    result = RetentionService(repository).run_once(dry_run=True)
    loaded = repository.get(expired.audit_id)

    assert result.deleted == 0
    assert loaded is not None
    assert any(event.event_type == "retention_dry_run" for event in loaded.events)
