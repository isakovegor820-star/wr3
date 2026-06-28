"""Bug-bounty scope ingestion (Immunefi).

Turns the public Immunefi bounties feed into wr3 ScoutTargets carrying a
``BountyContext`` (program, payout ceiling, submission URL). Only in-scope
smart-contract assets on chains wr3 supports are emitted, so the scout autopilot
can prioritise paying, in-scope targets and run fork-PoC against the live
address. Disclosure stays manual and Immunefi-routed.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import EVM_ADDRESS_RE, BountyContext, ScoutTarget

# Exact explorer host -> chain. Only wr3-supported EVM chains; anything else
# (polygonscan, optimistic.etherscan.io, snowtrace, zksync, ...) is skipped so we
# never queue a target we cannot actually analyse. Note the exact-host match
# keeps optimistic.etherscan.io from being treated as Ethereum.
EXPLORER_HOST_CHAIN: dict[str, Chain] = {
    "etherscan.io": Chain.ETHEREUM,
    "arbiscan.io": Chain.ARBITRUM,
    "basescan.org": Chain.BASE,
    "bscscan.com": Chain.BSC,
}

_ADDRESS_IN_URL_RE = re.compile(r"/address/(0x[0-9a-fA-F]{40})")


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def chain_address_from_asset_url(url: str) -> tuple[Chain, str] | None:
    if not url:
        return None
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return None
    chain = EXPLORER_HOST_CHAIN.get(host)
    if chain is None:
        return None
    match = _ADDRESS_IN_URL_RE.search(url)
    if not match:
        return None
    address = match.group(1)
    if not EVM_ADDRESS_RE.match(address):
        return None
    return chain, address


def _target_for(chain: Chain, address: str, program: str, slug: str, bounty: BountyContext) -> ScoutTarget:
    return ScoutTarget(
        source="immunefi",
        protocol_name=program,
        slug=slug or program.lower().replace(" ", "-"),
        category="bug_bounty",
        chain=chain,
        address=address,
        official_url=bounty.url,
        bounty=bounty,
        contact_instructions=[
            "Цель в активной программе Immunefi — раскрытие ТОЛЬКО через Immunefi, не пиши команде напрямую.",
            "Сверь точный scope и severity-классификацию в программе до сабмита.",
            "Никаких mainnet-транзакций: PoC гоняем только на форке/локально.",
        ],
        limitations=[
            "immunefi_in_scope_address_verify_exact_scope",
            "immunefi_submit_via_program_not_direct_contact",
            "passive_scan_only_no_auto_disclosure",
        ],
    )


def normalize_immunefi_bounties(
    payload: Any,
    *,
    min_payout_usd: float = 0.0,
    limit: int | None = None,
    max_per_program: int | None = None,
) -> list[ScoutTarget]:
    """Flatten the Immunefi bounties feed into ScoutTargets, highest payout first.

    De-duplicates by (chain, address): if the same contract appears in several
    programs we keep the first (highest-payout) occurrence after the sort.
    ``max_per_program`` caps how many in-scope contracts a single program may
    contribute, so one mega-bounty (e.g. LayerZero) cannot monopolise a cycle.
    """
    if not isinstance(payload, list):
        raise ValueError("immunefi_bounties_list_required")

    bounties = sorted(
        (item for item in payload if isinstance(item, dict)),
        key=lambda item: _float_or_none(item.get("maxBounty")) or 0.0,
        reverse=True,
    )

    targets: list[ScoutTarget] = []
    seen: set[tuple[Chain, str]] = set()
    for bounty in bounties:
        program = str(bounty.get("project") or bounty.get("slug") or "").strip()
        if not program:
            continue
        max_payout = _float_or_none(bounty.get("maxBounty"))
        if min_payout_usd and (max_payout is None or max_payout < min_payout_usd):
            continue
        slug = str(bounty.get("slug") or "").strip()
        url = f"https://immunefi.com/bounty/{slug}/" if slug else "https://immunefi.com/explore/"
        context = BountyContext(
            platform="immunefi",
            program=program,
            url=url,
            max_payout_usd=max_payout,
            asset_type="smart_contract",
        )
        program_count = 0
        for asset in bounty.get("assets") or []:
            if not isinstance(asset, dict) or asset.get("type") != "smart_contract":
                continue
            parsed = chain_address_from_asset_url(str(asset.get("url") or ""))
            if parsed is None:
                continue
            chain, address = parsed
            key = (chain, address.lower())
            if key in seen:
                continue
            seen.add(key)
            targets.append(_target_for(chain, address, program, slug, context))
            program_count += 1
            if limit is not None and len(targets) >= limit:
                return targets
            if max_per_program is not None and program_count >= max_per_program:
                break
    return targets
