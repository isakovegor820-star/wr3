"""Tests for the LLM budget protection + low-value-scan skip (navy cost control)."""
import pytest

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import CreateAuditRequest
from wr3_api.services import llm_triage
from wr3_api.services.audit_service import AuditService
from wr3_api.services.llm_triage import _llm_budget_consume, worth_llm_triage

VULN = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Bank { mapping(address=>uint256) public balances;
 function deposit() external payable { balances[msg.sender]+=msg.value; }
 function withdraw() external { uint256 a=balances[msg.sender]; require(a>0); (bool ok,)=msg.sender.call{value:a}(""); require(ok); balances[msg.sender]=0; } }
"""


@pytest.mark.asyncio
async def test_worth_llm_triage_gates_clean_and_bytecode(monkeypatch):
    svc = AuditService()
    rec = await svc.create_audit(
        CreateAuditRequest(chain=Chain.BASE, address="0x" + "4" * 40, source=VULN)
    )
    await svc.process_audit(rec.audit_id)
    record = svc.get_record(rec.audit_id)

    assert record.findings  # the reentrancy is flagged
    assert worth_llm_triage(record) is True  # source-mode scan with findings -> spend

    record.limitations.append("bytecode_only_limited_scan")
    assert worth_llm_triage(record) is False  # bytecode-only -> skip the LLM

    record.limitations = [lim for lim in record.limitations if "bytecode" not in lim]
    record.findings = []
    assert worth_llm_triage(record) is False  # clean scan -> nothing to triage


def test_in_memory_budget_cap_is_enforced(monkeypatch):
    monkeypatch.setenv("WR3_DATABASE_URL", "")  # force the in-memory path
    monkeypatch.setenv("WR3_LLM_MAX_CALLS_PER_DAY", "3")
    get_settings.cache_clear()
    llm_triage._llm_calls_today = 0
    llm_triage._llm_calls_date = None
    try:
        assert _llm_budget_consume() is True
        assert _llm_budget_consume() is True
        assert _llm_budget_consume() is True
        assert _llm_budget_consume() is False  # 4th call blocked at the cap
    finally:
        llm_triage._llm_calls_today = 0
        llm_triage._llm_calls_date = None
        get_settings.cache_clear()
