"""Tests for the 'turn findings into money' surface: /money + submit destination."""
from types import SimpleNamespace

import pytest

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain, Exploitability, Severity
from wr3_api.domain.schemas import BountyContext, CreateAuditRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.telegram_bot import TelegramCommandBot

VULN = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Bank { mapping(address=>uint256) public balances;
 function deposit() external payable { balances[msg.sender]+=msg.value; }
 function withdraw() external { uint256 a=balances[msg.sender]; require(a>0); (bool ok,)=msg.sender.call{value:a}(""); require(ok); balances[msg.sender]=0; } }
"""


def _bot(svc: AuditService) -> TelegramCommandBot:
    status = SimpleNamespace(running=True, healthy=True, cycle_count=1, drained_total=0, last_error=None)
    return TelegramCommandBot(
        audit_service=svc, scout_autopilot=SimpleNamespace(status=lambda: status), settings=get_settings()
    )


async def _confirmed_money_record(svc: AuditService, *, payout=1_000_000, program="MegaDeFi"):
    rec = await svc.create_audit(
        CreateAuditRequest(chain=Chain.BASE, address="0x" + "5" * 40, source=VULN)
    )
    await svc.process_audit(rec.audit_id)
    record = svc.get_record(rec.audit_id)
    assert record.findings
    record.findings[0].severity = Severity.HIGH
    record.findings[0].exploitability = Exploitability.CONFIRMED
    record.request.bounty = BountyContext(
        platform="immunefi", program=program, url="https://immunefi.com/bounty/mega/", max_payout_usd=payout
    )
    svc.save_record(record)
    return record


@pytest.mark.asyncio
async def test_money_findings_returns_confirmed_in_scope():
    svc = AuditService()
    await _confirmed_money_record(svc)
    money = svc.money_findings(limit=10)
    assert money
    assert money[0]["program"] == "MegaDeFi"
    assert money[0]["payout_usd"] == 1_000_000
    assert money[0]["url"] == "https://immunefi.com/bounty/mega/"


@pytest.mark.asyncio
async def test_money_findings_excludes_unconfirmed():
    svc = AuditService()
    rec = await svc.create_audit(
        CreateAuditRequest(chain=Chain.BASE, address="0x" + "6" * 40, source=VULN)
    )
    await svc.process_audit(rec.audit_id)  # heuristic findings, not forge-confirmed
    assert svc.money_findings(limit=10) == []  # nothing confirmed -> nothing to submit


@pytest.mark.asyncio
async def test_cmd_money_renders_payout_program_and_cta():
    svc = AuditService()
    await _confirmed_money_record(svc)
    out = _bot(svc)._cmd_money()
    assert "MegaDeFi" in out
    assert "1 000 000" in out  # payout, space-grouped
    assert "/report" in out


def test_cmd_money_empty_is_friendly():
    out = _bot(AuditService())._cmd_money()
    assert "Пока нет" in out


@pytest.mark.asyncio
async def test_report_includes_submit_destination():
    svc = AuditService()
    record = await _confirmed_money_record(svc)
    out = _bot(svc)._cmd_report(str(record.audit_id)[:8])
    assert "Куда подать" in out
    assert "immunefi.com/bounty/mega" in out
