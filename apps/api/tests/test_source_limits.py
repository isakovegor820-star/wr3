import pytest

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import CreateAuditRequest
from wr3_api.services.audit_service import AuditService


@pytest.mark.asyncio
async def test_service_rejects_source_over_configured_byte_limit(monkeypatch):
    monkeypatch.setenv("WR3_MAX_SOURCE_BYTES", "12")
    get_settings.cache_clear()
    service = AuditService()

    record = await service.create_audit(
        CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
            source="contract Vault { function ping() external {} }",
        )
    )

    assert record.state == "rejected"
    assert "source_exceeds_max_source_bytes" in record.limitations
    assert any(
        event.event_type == "state_transition" and event.payload["to"] == "rejected"
        for event in record.events
    )
    get_settings.cache_clear()
