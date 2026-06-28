"""Driver for scripts/demo_autonomous_loop.sh — runs the real wr3 pipeline against
a live (anvil) deployment and narrates the autonomous loop end-to-end."""
import asyncio
import sys

from wr3_api.core.config import get_settings

get_settings.cache_clear()  # pick up WR3_POC_FORK_RPC_URL set by the wrapper

from wr3_api.domain.enums import Chain, Tier, UserIntent, Visibility
from wr3_api.domain.schemas import BountyContext, CreateAuditRequest, DisclosurePacketRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.auth import AuthContext


async def main(vault: str, src: str) -> int:
    service = AuditService()
    alerts: list[tuple[str, str]] = []

    async def _capture(*, title: str, body: str):
        alerts.append((title, body))
        return {"sent": 1}

    service._notifications.send_owner_alert = _capture  # capture instead of hitting Telegram
    reviewer = AuthContext(user_id="wr3-scout", provider="system", subject="scout", is_reviewer=True)

    # 🎯 SCOPE — what the Immunefi source produces for this in-scope address.
    bounty = BountyContext(
        platform="immunefi", program="DemoVault",
        url="https://immunefi.com/bounty/demovault/", max_payout_usd=1_000_000, asset_type="smart_contract",
    )
    print(f"      🎯 scope: in-scope Immunefi target | program={bounty.program} | up to ${int(bounty.max_payout_usd):,}")

    rec = await service.create_audit(
        CreateAuditRequest(
            chain=Chain.BASE, address=vault, source=src, requested_depth="deep",
            user_intent=UserIntent.MONITORING, visibility=Visibility.PRIVATE, tier=Tier.TEAM, bounty=bounty,
        ),
        reviewer,
    )
    print(f"      🔬 analysing {vault[:12]}… (deep, autonomous monitoring)")
    await service.process_audit(rec.audit_id)
    rec = service.get_record(rec.audit_id)

    poc = next((e for e in rec.engine_runs if e.engine == "foundry_poc"), None)
    strat = fork = None
    for ev in rec.events:
        if ev.event_type == "poc_worker_result":
            strat, fork = ev.payload.get("strategy"), ev.payload.get("fork_mode")
    confirmed = [f for f in rec.findings if f.exploitability == "confirmed"]
    reentrancy = next((f for f in confirmed if "reentr" in f.taxonomy.wr3_category.lower()), None)

    print(f"      💥 fork-PoC: status={poc.status if poc else '-'} strategy={strat} fork_mode={fork}  "
          f"-> drained the LIVE contract by address")
    print(f"      ✓ findings: {len(rec.findings)} total, {len(confirmed)} CONFIRMED")
    if reentrancy:
        print(f"        └─ [{reentrancy.severity}] {reentrancy.taxonomy.wr3_category}: "
              f"{reentrancy.summary[:48]} (poc={reentrancy.evidence.poc_status})")

    pkt = None
    if reentrancy:
        pkt = service.prepare_disclosure_packet(
            DisclosurePacketRequest(
                audit_id=rec.audit_id, finding_id=reentrancy.id,
                official_contact=bounty.url, contact_source="bug_bounty_portal",
            ),
            reviewer,
        )
        print(f"      📦 disclosure packet: program={pkt.bounty_program} "
              f"payout=${int(pkt.bounty_max_payout_usd or 0):,} submit={pkt.bounty_submission_url}")
        print(f"        └─ confirmed_by_poc={pkt.confirmed_by_poc} | state={pkt.readiness_state}")
        reason = (pkt.bounty_acceptance_reason or "").splitlines()
        if reason:
            print(f"        └─ {reason[0]}")

    if alerts:
        print(f"      🔔 owner alert fired: \"{alerts[0][0]}\"")

    ok = bool(
        poc and poc.status == "confirmed" and fork is True and reentrancy is not None
        and pkt and pkt.bounty_program == "DemoVault" and pkt.confirmed_by_poc and alerts
    )
    print()
    print("════════════════════════════════════════════════════════════════")
    print(" RESULT:", "✅ FULL AUTONOMOUS LOOP CONFIRMED END-TO-END" if ok else "❌ INCOMPLETE")
    print(" scope → analysis → fork-PoC on live contract → submission packet → owner alert")
    print("════════════════════════════════════════════════════════════════")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2])))
