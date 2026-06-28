import pytest

from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import BountyContext, ScoutAutopilotRunRequest, ScoutTarget
from wr3_api.services.audit_service import AuditService
from wr3_api.services.bounty_sources import chain_address_from_asset_url, normalize_immunefi_bounties
from wr3_api.services.scout_autopilot import ScoutAutopilot, _merge_targets


def test_explorer_url_maps_only_supported_chains():
    assert chain_address_from_asset_url("https://etherscan.io/address/0x" + "1" * 40)[0] == Chain.ETHEREUM
    assert chain_address_from_asset_url("https://arbiscan.io/address/0x" + "2" * 40)[0] == Chain.ARBITRUM
    assert chain_address_from_asset_url("https://basescan.org/address/0x" + "3" * 40)[0] == Chain.BASE
    assert chain_address_from_asset_url("https://bscscan.com/address/0x" + "4" * 40)[0] == Chain.BSC
    # unsupported chains (and the optimism subdomain of etherscan) must be skipped
    assert chain_address_from_asset_url("https://optimistic.etherscan.io/address/0x" + "5" * 40) is None
    assert chain_address_from_asset_url("https://polygonscan.com/address/0x" + "6" * 40) is None


_FIXTURE = [
    {"project": "GMX", "slug": "gmx", "maxBounty": "5000000", "assets": [
        {"type": "smart_contract", "url": "https://arbiscan.io/address/0x489ee077994B6658eAfA855C308275EAd8097C4A"},
        {"type": "smart_contract", "url": "https://optimistic.etherscan.io/address/0x" + "d" * 40},
        {"type": "websites_and_applications", "url": "https://gmx.io"},
    ]},
    {"project": "SmallFry", "slug": "smallfry", "maxBounty": "10000", "assets": [
        {"type": "smart_contract", "url": "https://etherscan.io/address/0x" + "9" * 40},
    ]},
    {"project": "BaseThing", "slug": "base-thing", "maxBounty": "250000", "assets": [
        {"type": "smart_contract", "url": "https://basescan.org/address/0x" + "a" * 40},
    ]},
]


def test_normalize_immunefi_filters_payout_and_unsupported_assets_and_sorts():
    targets = normalize_immunefi_bounties(_FIXTURE, min_payout_usd=50_000)
    # SmallFry dropped (payout < 50k); only one supported asset survives per program
    assert [t.protocol_name for t in targets] == ["GMX", "BaseThing"]  # sorted by payout desc
    gmx = targets[0]
    assert gmx.source == "immunefi"
    assert gmx.chain == Chain.ARBITRUM
    assert gmx.bounty is not None
    assert gmx.bounty.platform == "immunefi"
    assert gmx.bounty.max_payout_usd == 5_000_000
    assert gmx.bounty.url == "https://immunefi.com/bounty/gmx/"
    assert "immunefi_submit_via_program_not_direct_contact" in gmx.limitations


def test_normalize_immunefi_dedupes_same_address_across_programs():
    addr = "0x" + "b" * 40
    payload = [
        {"project": "Big", "slug": "big", "maxBounty": "900000", "assets": [
            {"type": "smart_contract", "url": f"https://etherscan.io/address/{addr}"}]},
        {"project": "Small", "slug": "small", "maxBounty": "100000", "assets": [
            {"type": "smart_contract", "url": f"https://etherscan.io/address/{addr}"}]},
    ]
    targets = normalize_immunefi_bounties(payload)
    assert len(targets) == 1
    assert targets[0].protocol_name == "Big"  # higher payout wins after the sort


def test_normalize_immunefi_rejects_non_list():
    with pytest.raises(ValueError):
        normalize_immunefi_bounties({"not": "a list"})


def test_merge_targets_prioritises_primary_and_dedupes():
    addr = "0x" + "c" * 40
    immunefi = [ScoutTarget(source="immunefi", protocol_name="P", slug="p", chain=Chain.BASE, address=addr,
                            bounty=BountyContext(program="P"))]
    defillama = [ScoutTarget(source="defillama_protocols", protocol_name="P-llama", slug="p", chain=Chain.BASE, address=addr.upper())]
    merged = _merge_targets(immunefi, defillama)
    assert len(merged) == 1
    assert merged[0].source == "immunefi"  # primary (bounty) wins the dedupe


class _FakeDiscovery:
    def __init__(self, immunefi, defillama):
        self._immunefi = immunefi
        self._defillama = defillama

    async def discover_immunefi_targets(self, **_kwargs):
        return list(self._immunefi)

    async def discover_all_supported_networks(self, **_kwargs):
        return list(self._defillama)


@pytest.mark.asyncio
async def test_autopilot_queues_bounty_targets_first_and_propagates_context():
    bounty_target = ScoutTarget(
        source="immunefi", protocol_name="GMX", slug="gmx", chain=Chain.ARBITRUM,
        address="0x489ee077994B6658eAfA855C308275EAd8097C4A",
        bounty=BountyContext(program="GMX", max_payout_usd=5_000_000, url="https://immunefi.com/bounty/gmx/"),
    )
    llama_target = ScoutTarget(
        source="defillama_protocols", protocol_name="Lido", slug="lido", chain=Chain.ETHEREUM,
        address="0x5a98fcbea516cf06857215779fd812ca3bef1b32",
    )
    service = AuditService()
    autopilot = ScoutAutopilot(
        audit_service=service,
        discovery_service=_FakeDiscovery([bounty_target], [llama_target]),
    )

    result = await autopilot.run_now(ScoutAutopilotRunRequest(process_queued=False))

    assert result.source == "immunefi+defillama_protocols"
    assert result.targets[0].source == "immunefi"  # bounty target prioritised
    assert any(limitation.startswith("immunefi_bounty_targets:1") for limitation in result.limitations)

    bounty_audit = next(a for a in result.audits if a.address == bounty_target.address)
    record = service.get_record(bounty_audit.audit_id)
    assert record.request.bounty is not None
    assert record.request.bounty.program == "GMX"
    assert any(lim.startswith("autopilot_immunefi_in_scope:GMX") for lim in record.limitations)
