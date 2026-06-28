import shutil

import pytest

from wr3_api.domain.enums import Chain, Tier
from wr3_api.domain.schemas import AuditRecord, CreateAuditRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.fuzzing import FuzzingWorker

_BUGGY_BANK = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Bank {
    mapping(address => uint256) public balances;
    function deposit() external payable { balances[msg.sender] += msg.value; }
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
        // BUG: never zeroes balances[msg.sender] -> insolvency
    }
}
"""

_CORRECT_BANK = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Bank {
    mapping(address => uint256) public balances;
    function deposit() external payable { balances[msg.sender] += msg.value; }
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        balances[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
"""


_BUGGY_ERC20 = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Tok {
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;
    constructor(uint256 s) { totalSupply = s; balanceOf[msg.sender] = s; }
    function transfer(address to, uint256 amt) external returns (bool) {
        balanceOf[to] += amt;   // BUG: never debits msg.sender -> supply inflation
        return true;
    }
}
"""

_CORRECT_ERC20 = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Tok {
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;
    constructor(uint256 s) { totalSupply = s; balanceOf[msg.sender] = s; }
    function transfer(address to, uint256 amt) external returns (bool) {
        require(balanceOf[msg.sender] >= amt, "insufficient");
        balanceOf[msg.sender] -= amt;
        balanceOf[to] += amt;
        return true;
    }
}
"""


def _deep_record(source: str) -> AuditRecord:
    return AuditRecord(
        request=CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
            source=source,
            requested_depth="deep",
            tier=Tier.TEAM,
        )
    )


@pytest.mark.skipif(shutil.which("medusa") is None, reason="medusa not installed")
@pytest.mark.asyncio
async def test_medusa_finds_solvency_violation_in_buggy_bank():
    worker = FuzzingWorker()
    result = await worker.run(_deep_record(_BUGGY_BANK), [])
    assert result.status == "counterexample_found"
    assert result.violated_properties
    assert result.counterexample


@pytest.mark.skipif(shutil.which("medusa") is None, reason="medusa not installed")
@pytest.mark.asyncio
async def test_medusa_passes_correct_bank():
    worker = FuzzingWorker()
    result = await worker.run(_deep_record(_CORRECT_BANK), [])
    assert result.status == "no_violations"
    assert not result.violated_properties


@pytest.mark.skipif(shutil.which("medusa") is None, reason="medusa not installed")
@pytest.mark.asyncio
async def test_medusa_finds_supply_inflation_in_buggy_erc20():
    worker = FuzzingWorker()
    result = await worker.run(_deep_record(_BUGGY_ERC20), [])
    assert result.status == "counterexample_found"
    assert any("supply" in prop for prop in result.violated_properties)


@pytest.mark.skipif(shutil.which("medusa") is None, reason="medusa not installed")
@pytest.mark.asyncio
async def test_medusa_passes_correct_erc20():
    worker = FuzzingWorker()
    result = await worker.run(_deep_record(_CORRECT_ERC20), [])
    assert result.status == "no_violations"
    assert not result.violated_properties


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
        "fuzzing_no_supported_invariant_shape",
        "fuzzing_requires_source",
    }
    assert fuzz_runs[0].artifact_uri is not None or "fuzzing_status_artifact_requires_encryption" in record.limitations
    assert any(event.event_type == "fuzzing_worker_result" for event in record.events)


@pytest.mark.asyncio
async def test_fuzzing_worker_does_not_block_legacy_hobby_tier():
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
    assert result.error in {
        "fuzzing_binaries_missing",
        "fuzzing_no_supported_invariant_shape",
        "fuzzing_requires_source",
    }
