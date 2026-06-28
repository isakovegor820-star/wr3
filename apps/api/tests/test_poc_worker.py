import shutil

import pytest

from wr3_api.domain.enums import Chain, Exploitability, Severity, Tier
from wr3_api.domain.schemas import AuditRecord, ContractRef, CreateAuditRequest, Finding, Taxonomy
from wr3_api.services.audit_service import AuditService
from wr3_api.services.poc import (
    ForkContext,
    FoundryPocWorker,
    build_foundry_test,
    build_reentrancy_exploit,
    ensure_solidity_pragma,
)

_OWN_VULN = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Vault {
    address public owner;
    constructor() { owner = msg.sender; }
    function setOwner(address n) public { owner = n; }
}
"""
_OWN_SAFE = _OWN_VULN.replace("{ owner = n; }", '{ require(msg.sender == owner, "only"); owner = n; }')
_SD_VULN = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Killable {
    address public owner;
    constructor() { owner = msg.sender; }
    function kill() public { selfdestruct(payable(msg.sender)); }
}
"""
_SD_SAFE = _SD_VULN.replace(
    "{ selfdestruct(payable(msg.sender)); }",
    '{ require(msg.sender == owner, "only"); selfdestruct(payable(msg.sender)); }',
)
_TXO_VULN = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Phishable {
    address public owner;
    constructor() { owner = msg.sender; }
    function setOwner(address n) external { require(tx.origin == owner, "no"); owner = n; }
}
"""
_TXO_SAFE = _TXO_VULN.replace("tx.origin == owner", "msg.sender == owner")
_DC_VULN = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Proxyish {
    address public owner;
    constructor() { owner = msg.sender; }
    function execute(address t, bytes calldata d) external { (bool ok, ) = t.delegatecall(d); require(ok); }
}
"""
_DC_SAFE = _DC_VULN.replace(
    "function execute(address t, bytes calldata d) external {",
    'function execute(address t, bytes calldata d) external { require(msg.sender == owner, "no");',
)
_MINT_VULN = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Tok {
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;
    function mint(address to, uint256 amt) external { balanceOf[to] += amt; totalSupply += amt; }
}
"""
_MINT_SAFE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Tok {
    address public owner;
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;
    constructor() { owner = msg.sender; }
    function mint(address to, uint256 amt) external { require(msg.sender == owner, "no"); balanceOf[to] += amt; totalSupply += amt; }
}
"""


def _candidate(source: str, category: str, summary: str) -> tuple[AuditRecord, Finding]:
    record = AuditRecord(
        request=CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
            source=source,
            requested_depth="deep",
        )
    )
    finding = Finding(
        audit_id=str(record.audit_id), chain=Chain.BASE, contract=ContractRef(name="T"),
        taxonomy=Taxonomy(wr3_category=category), severity=Severity.HIGH, confidence=0.9,
        exploitability=Exploitability.THEORETICAL, sources=["slither"],
        summary=summary, description=summary, impact="i", recommendation="r",
    )
    return record, finding


@pytest.mark.skipif(shutil.which("forge") is None, reason="foundry not installed")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,category,summary,strategy",
    [
        (_OWN_VULN, "access_control", "Unprotected setOwner: anyone can take ownership", "ownership_takeover"),
        (_SD_VULN, "static_analysis", "Suicidal: unprotected selfdestruct", "selfdestruct"),
        (_TXO_VULN, "access_control", "tx.origin used for authorization (phishing)", "tx_origin"),
        (_DC_VULN, "access_control", "controlled delegatecall enables takeover", "delegatecall"),
        (_MINT_VULN, "access_control", "anyone can mint tokens, infinite supply", "erc20_mint"),
    ],
)
async def test_poc_confirms_new_exploit_classes(source, category, summary, strategy):
    record, finding = _candidate(source, category, summary)
    result = await FoundryPocWorker().run(record, [finding])
    assert result.status == "confirmed"
    assert result.strategy == strategy
    assert result.confirmed_finding_ids == (finding.id,)


@pytest.mark.skipif(shutil.which("forge") is None, reason="foundry not installed")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,category,summary",
    [
        (_OWN_SAFE, "access_control", "setOwner guarded by onlyOwner"),
        (_SD_SAFE, "static_analysis", "selfdestruct guarded by onlyOwner"),
        (_TXO_SAFE, "access_control", "access control authorization on setOwner"),
        (_DC_SAFE, "access_control", "delegatecall takeover attempt"),
        (_MINT_SAFE, "access_control", "anyone can mint infinite supply"),
    ],
)
async def test_poc_does_not_confirm_guarded_contracts(source, category, summary):
    record, finding = _candidate(source, category, summary)
    result = await FoundryPocWorker().run(record, [finding])
    assert result.status != "confirmed"
    assert result.confirmed_finding_ids == ()


def test_fork_mode_codegen_uses_createselectfork_and_address_cast():
    _, finding = _candidate("contract Bank {}", "reentrancy", "reentrancy")
    fork = ForkContext(rpc_url="http://127.0.0.1:8545", address="0xabcDEF0000000000000000000000000000000123")
    src = build_reentrancy_exploit("Bank", finding, fork)
    assert 'vm.createSelectFork("http://127.0.0.1:8545")' in src
    assert 'address(bytes20(hex"abcdef0000000000000000000000000000000123"))' in src
    assert "target.deposit{value: pool}" not in src  # fork mode does not seed; the live pool is real
    assert "WR3_CONFIRMED_EXPLOIT_ASSERTION" in src


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
async def test_foundry_worker_does_not_block_legacy_free_tier():
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
    assert result.error == "poc_no_high_or_critical_candidates"


def test_foundry_poc_generation_wraps_source_and_previous_error_safely():
    source = ensure_solidity_pragma("contract Vault {}")
    harness = build_foundry_test([], 2, "compiler failed */ but should stay in comment")

    assert source.startswith("pragma solidity")
    assert "attempt 2" in harness
    assert "* /" in harness
    assert "WR3_CONFIRMED_EXPLOIT_ASSERTION" not in harness
