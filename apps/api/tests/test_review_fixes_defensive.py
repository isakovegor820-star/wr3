"""Regression tests for the defensive-cluster review fixes (M8, M3, M1)."""
import asyncio

import pytest

from wr3_api.domain.enums import AuditState, Chain
from wr3_api.domain.schemas import CreateAuditRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.scout_autopilot import ScoutAutopilot
from wr3_api.services.target_discovery import normalize_defillama_protocols

VULN = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Bank { mapping(address=>uint256) public balances;
 function deposit() external payable { balances[msg.sender]+=msg.value; }
 function withdraw() external { uint256 a=balances[msg.sender]; require(a>0); (bool ok,)=msg.sender.call{value:a}(""); require(ok); balances[msg.sender]=0; } }
"""


class _EmptyDiscovery:
    async def discover_immunefi_targets(self, **_kwargs):
        return []

    async def discover_all_supported_networks(self, **_kwargs):
        return []


# ---- M8: a malformed tvl in the untrusted DeFiLlama feed must not crash --------
def test_malformed_tvl_does_not_crash_discovery():
    payload = [
        {"name": "ok", "tvl": 5_000_000, "chains": ["Ethereum"], "address": "0x" + "1" * 40},
        {"name": "string-tvl", "tvl": "N/A", "chains": ["Ethereum"]},          # float("N/A") -> ValueError
        {"name": "dict-tvl", "tvl": {"weird": 1}, "chains": ["Ethereum"]},     # float(dict) -> TypeError
        {"name": "none-tvl", "tvl": None, "chains": ["Ethereum"]},
    ]
    # Must not raise (previously float() in the sort key aborted the whole cycle).
    out = normalize_defillama_protocols(payload, limit=5, min_tvl_usd=0)
    assert isinstance(out, list)


# ---- M3: in-process audit concurrency is bounded by the semaphore --------------
@pytest.mark.asyncio
async def test_bounded_process_caps_concurrency():
    autopilot = ScoutAutopilot(audit_service=AuditService(), discovery_service=_EmptyDiscovery())
    autopilot._process_semaphore = asyncio.Semaphore(2)
    running = 0
    peak = 0

    async def fake_process(_audit_id):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.03)
        running -= 1

    autopilot._audit_service.process_audit = fake_process
    await asyncio.gather(*[autopilot._bounded_process(i) for i in range(8)])
    assert peak <= 2  # never more than the semaphore allows


# ---- M1: re-processing a record does not duplicate findings/engine_runs --------
@pytest.mark.asyncio
async def test_reprocess_does_not_duplicate_findings():
    svc = AuditService()
    rec = await svc.create_audit(
        CreateAuditRequest(chain=Chain.BASE, address="0x" + "2" * 40, source=VULN)
    )
    await svc.process_audit(rec.audit_id)
    first = svc.get_record(rec.audit_id)
    n_findings = len(first.findings)
    n_runs = len(first.engine_runs)
    assert n_findings > 0  # the heuristic adapter flags the reentrancy

    # Simulate a retry re-queue (retry() only fires from FAILED/PARTIAL/NEEDS_SOURCE,
    # but the queue + worker both end in this exact state: QUEUED then re-process).
    first.state = AuditState.QUEUED
    svc.save_record(first)
    await svc.process_audit(rec.audit_id)

    second = svc.get_record(rec.audit_id)
    assert len(second.findings) == n_findings  # reset, not doubled
    assert len(second.engine_runs) == n_runs
