import pytest

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import CreateAuditRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.safe_harbor import SafeHarborRegistry


def test_safe_harbor_registry_loads_json_entries(monkeypatch):
    monkeypatch.setenv(
        "WR3_SAFE_HARBOR_REGISTRY_JSON",
        '{"contracts":[{"chain":"base","address":"0x0000000000000000000000000000000000000000"}]}',
    )
    get_settings.cache_clear()

    registry = SafeHarborRegistry()

    assert registry.is_registered(Chain.BASE, "0x0000000000000000000000000000000000000000") is True
    assert registry.is_registered(Chain.ETHEREUM, "0x0000000000000000000000000000000000000000") is False
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_public_project_summary_uses_safe_harbor_registry():
    registry = SafeHarborRegistry(entries={(Chain.BASE, "0x0000000000000000000000000000000000000000")})
    service = AuditService(safe_harbor_registry=registry)
    record = await service.create_audit(
        CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
            source="contract Plain { function ping() external pure returns (uint256) { return 1; } }",
        )
    )
    await service.process_audit(record.audit_id)

    public = service.public_project(Chain.BASE, "0x0000000000000000000000000000000000000000")

    assert public.safe_harbor_status is True
