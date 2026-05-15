import pytest

from wr3_api.domain.enums import Chain, Tier
from wr3_api.domain.schemas import AuditRecord, CreateAuditRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.fuzzing import FuzzingWorker


@pytest.mark.asyncio
async def test_deep_team_audit_records_fuzzing_worker_result():
    service = AuditService()
    record = await service.create_audit(
        CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
            source="contract Plain { function ping() external pure returns (uint256) { return 1; } }",
            requested_depth="deep",
            tier=Tier.TEAM,
        )
    )

    await service.process_audit(record.audit_id)
    record = service.get_record(record.audit_id)

    fuzz_runs = [run for run in record.engine_runs if run.engine == "ai_fuzzing"]
    assert record.state == "completed"
    assert len(fuzz_runs) == 1
    assert fuzz_runs[0].status == "skipped"
    assert fuzz_runs[0].error in {
        "fuzzing_binaries_missing",
        "fuzzing_generation_stub_requires_invariant_sandbox",
    }
    assert fuzz_runs[0].artifact_uri is not None or "fuzzing_status_artifact_requires_encryption" in record.limitations
    assert any(event.event_type == "fuzzing_worker_result" for event in record.events)


@pytest.mark.asyncio
async def test_fuzzing_worker_blocks_non_team_tiers():
    worker = FuzzingWorker()
    record = AuditRecord(
        request=CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
            source="contract Vault {}",
            requested_depth="deep",
            tier=Tier.HOBBY,
        )
    )

    result = await worker.run(record, [])

    assert result.status == "skipped"
    assert result.error == "fuzzing_requires_team_or_pro_tier"
