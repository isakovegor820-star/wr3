"""The owner alert must scream MONEY when a finding lands in a paying program."""
import pytest

from wr3_api.domain.enums import Chain, Exploitability, Severity, UserIntent
from wr3_api.domain.schemas import BountyContext, CreateAuditRequest
from wr3_api.services.audit_service import AuditService

VULN = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Bank { mapping(address=>uint256) public balances;
 function deposit() external payable { balances[msg.sender]+=msg.value; }
 function withdraw() external { uint256 a=balances[msg.sender]; require(a>0); (bool ok,)=msg.sender.call{value:a}(""); require(ok); balances[msg.sender]=0; } }
"""


class _StubNotifier:
    def __init__(self):
        self.sent = []

    async def send_owner_alert(self, *, title, body):
        self.sent.append((title, body))
        return {"sent": 1}


async def _monitoring_record(svc, *, bounty):
    rec = await svc.create_audit(
        CreateAuditRequest(
            chain=Chain.BASE,
            address="0x" + "7" * 40,
            source=VULN,
            user_intent=UserIntent.MONITORING,
            bounty=bounty,
        )
    )
    await svc.process_audit(rec.audit_id)
    record = svc.get_record(rec.audit_id)
    record.findings[0].severity = Severity.HIGH
    record.findings[0].exploitability = Exploitability.CONFIRMED
    return record


@pytest.mark.asyncio
async def test_alert_screams_money_when_in_paying_scope():
    svc = AuditService()
    notifier = _StubNotifier()
    svc._notifications = notifier
    record = await _monitoring_record(
        svc,
        bounty=BountyContext(
            platform="immunefi", program="SmallDeFi",
            url="https://immunefi.com/bounty/small/", max_payout_usd=10_000,
        ),
    )
    notifier.sent.clear()
    await svc._maybe_alert_owner(record)

    assert notifier.sent
    title = notifier.sent[-1][0]
    assert "💰" in title and "ДЕНЬГИ" in title
    assert "10 000" in title  # the payout ceiling, space-grouped


@pytest.mark.asyncio
async def test_no_alert_for_candidate_only_finding():
    # confirmed_only defaults True: a candidate (not forge-proven) must NOT ping the
    # owner — on audited code candidates are almost all false positives.
    svc = AuditService()
    notifier = _StubNotifier()
    svc._notifications = notifier
    record = await _monitoring_record(
        svc, bounty=BountyContext(platform="immunefi", program="X", max_payout_usd=5000)
    )
    record.findings[0].exploitability = Exploitability.LIKELY  # candidate, not confirmed
    notifier.sent.clear()
    await svc._maybe_alert_owner(record)
    assert notifier.sent == []


@pytest.mark.asyncio
async def test_alert_stays_plain_when_not_in_paying_scope():
    svc = AuditService()
    notifier = _StubNotifier()
    svc._notifications = notifier
    record = await _monitoring_record(svc, bounty=None)  # no paying program
    notifier.sent.clear()
    await svc._maybe_alert_owner(record)

    assert notifier.sent
    title = notifier.sent[-1][0]
    assert "ДЕНЬГИ" not in title  # not a money alert — just a regular bug alert
