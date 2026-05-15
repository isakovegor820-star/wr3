import pytest

from wr3_api.domain.enums import Chain, Tier
from wr3_api.domain.schemas import AuditRecord, CreateAuditRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.poc import FoundryPocWorker, build_foundry_test, ensure_solidity_pragma


@pytest.mark.asyncio
async def test_standard_team_audit_records_foundry_poc_worker_result():
    service = AuditService()
    record = await service.create_audit(
        CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
            source="contract Vault { function auth(address a) public { require(tx.origin == a); } }",
            requested_depth="standard",
            tier=Tier.TEAM,
        )
    )
    await service.process_audit(record.audit_id)
    record = service.get_record(record.audit_id)

    assert record.state == "completed"
    poc_runs = [run for run in record.engine_runs if run.engine == "foundry_poc"]
    assert len(poc_runs) == 1
    assert poc_runs[0].status in {"skipped", "attempted"}
    assert poc_runs[0].error in {
        "foundry_binary_missing",
        "poc_generation_stub_requires_zdr_llm_sandbox",
        "poc_not_confirmed_after_retry_loop",
        "poc_artifact_requires_encryption",
    }
    assert poc_runs[0].artifact_uri is not None or "poc_status_artifact_requires_encryption" in record.limitations
    assert any(event.event_type == "poc_worker_result" for event in record.events)
    assert not any(
        event.payload.get("confirmed_finding_ids")
        for event in record.events
        if event.event_type == "poc_worker_result"
    )


@pytest.mark.asyncio
async def test_foundry_worker_blocks_free_tier_poc_attempts():
    worker = FoundryPocWorker()
    record = AuditRecord(
        request=CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
            source="contract Vault {}",
            requested_depth="standard",
            tier=Tier.FREE,
        )
    )

    result = await worker.run(record, [])

    assert result.status == "skipped"
    assert result.error == "poc_requires_team_or_pro_tier"


def test_foundry_poc_generation_wraps_source_and_previous_error_safely():
    source = ensure_solidity_pragma("contract Vault {}")
    harness = build_foundry_test([], 2, "compiler failed */ but should stay in comment")

    assert source.startswith("pragma solidity")
    assert "attempt 2" in harness
    assert "* /" in harness
    assert "WR3_CONFIRMED_EXPLOIT_ASSERTION" not in harness
