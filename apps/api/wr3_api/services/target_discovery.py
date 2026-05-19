from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from wr3_api.core.config import Settings, get_settings
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import EVM_ADDRESS_RE, ScoutTarget


SUPPORTED_CHAIN_ALIASES: dict[str, Chain] = {
    "ethereum": Chain.ETHEREUM,
    "eth": Chain.ETHEREUM,
    "base": Chain.BASE,
    "bsc": Chain.BSC,
    "binance": Chain.BSC,
    "binance smart chain": Chain.BSC,
    "bnb": Chain.BSC,
    "bnb chain": Chain.BSC,
    "arbitrum": Chain.ARBITRUM,
    "arbitrum one": Chain.ARBITRUM,
    "solana": Chain.SOLANA,
}

CHAIN_PRIORITY: tuple[Chain, ...] = (
    Chain.BASE,
    Chain.ETHEREUM,
    Chain.BSC,
    Chain.ARBITRUM,
    Chain.SOLANA,
)

SOLANA_ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class TargetDiscoveryService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def discover_defillama_protocols(
        self,
        *,
        limit: int = 10,
        min_tvl_usd: float = 0,
        chains: list[Chain] | None = None,
    ) -> list[ScoutTarget]:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(self._settings.defillama_protocols_url)
            response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("defillama_protocols_list_required")
        return normalize_defillama_protocols(
            payload,
            limit=limit,
            min_tvl_usd=min_tvl_usd,
            chains=chains or [],
        )

    async def discover_all_supported_networks(
        self,
        *,
        per_chain_limit: int = 3,
        min_tvl_usd: float = 0,
        chains: list[Chain] | None = None,
    ) -> list[ScoutTarget]:
        selected_chains = chains or list(CHAIN_PRIORITY)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self._settings.defillama_protocols_url)
            response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("defillama_protocols_list_required")

        targets: list[ScoutTarget] = []
        seen: set[tuple[Chain, str]] = set()
        for chain in selected_chains:
            for target in normalize_defillama_protocols(
                payload,
                limit=per_chain_limit,
                min_tvl_usd=min_tvl_usd,
                chains=[chain],
            ):
                key = (target.chain, target.address.lower())
                if key in seen:
                    continue
                seen.add(key)
                targets.append(target)
        return targets


def normalize_defillama_protocols(
    payload: list[Any],
    *,
    limit: int = 10,
    min_tvl_usd: float = 0,
    chains: list[Chain] | None = None,
) -> list[ScoutTarget]:
    selected: list[ScoutTarget] = []
    allowed = set(chains or [])
    sorted_payload = sorted(
        [item for item in payload if isinstance(item, dict)],
        key=lambda item: float(item.get("tvl") or 0),
        reverse=True,
    )
    for raw in sorted_payload:
        if len(selected) >= limit:
            break
        tvl = _float_or_none(raw.get("tvl"))
        if tvl is not None and tvl < min_tvl_usd:
            continue
        if str(raw.get("category") or "").lower() == "cex":
            continue
        target = target_from_defillama_protocol(raw, preferred_chains=list(allowed))
        if target is None:
            continue
        if allowed and target.chain not in allowed:
            continue
        selected.append(target)
    return selected


def target_from_defillama_protocol(
    raw: dict[str, Any],
    *,
    preferred_chains: list[Chain] | None = None,
) -> ScoutTarget | None:
    address_raw = str(raw.get("address") or "").strip()
    if not address_raw:
        return None
    chain, address = _chain_and_address(address_raw, raw.get("chains"), preferred_chains or [])
    if chain is None or address is None:
        return None
    if chain == Chain.SOLANA:
        if not SOLANA_ADDRESS_RE.match(address):
            return None
    elif not EVM_ADDRESS_RE.match(address):
        return None

    official_url = _clean_url(raw.get("url"))
    twitter_url = _twitter_url(raw.get("twitter"))
    domain = _domain_from_url(official_url)
    contact_instructions = [
        "Сначала проверь официальный сайт проекта: Security, Contact, Docs или Bug bounty.",
        "Если есть GitHub, ищи SECURITY.md или вкладку Security policy.",
        "Если проект есть на Immunefi/Hats/Cantina/Sherlock/Code4rena, сверяй scope до письма.",
        "Не отправляй PoC публично и не делай mainnet-транзакции.",
    ]
    limitations = [
        "defillama_protocol_address_may_be_token_or_protocol_pointer",
        "security_contact_needs_manual_verification",
        "passive_scan_only_no_auto_disclosure",
    ]
    return ScoutTarget(
        protocol_name=str(raw.get("name") or raw.get("slug") or "Unknown protocol"),
        slug=str(raw.get("slug") or raw.get("name") or "unknown"),
        category=str(raw.get("category")) if raw.get("category") else None,
        chain=chain,
        address=address,
        tvl_usd=_float_or_none(raw.get("tvl")),
        official_url=official_url,
        twitter_url=twitter_url,
        security_txt_url=f"https://{domain}/.well-known/security.txt" if domain else None,
        security_email_guess=f"security@{domain}" if domain else None,
        contact_instructions=contact_instructions,
        limitations=limitations,
    )


def _chain_and_address(
    address_raw: str,
    raw_chains: Any,
    preferred_chains: list[Chain],
) -> tuple[Chain | None, str | None]:
    if ":" in address_raw:
        prefix, address = address_raw.split(":", 1)
        chain = _chain_from_label(prefix)
        return chain, address.strip() if chain else None
    address = address_raw.strip()
    chain = _best_supported_chain(raw_chains, preferred_chains)
    return chain, address if chain else None


def _best_supported_chain(raw_chains: Any, preferred_chains: list[Chain] | None = None) -> Chain | None:
    if not isinstance(raw_chains, list):
        return Chain.ETHEREUM
    mapped = {_chain_from_label(str(item)) for item in raw_chains}
    mapped.discard(None)
    for chain in preferred_chains or []:
        if chain in mapped:
            return chain
    for chain in CHAIN_PRIORITY:
        if chain in mapped:
            return chain
    return None


def _chain_from_label(label: str) -> Chain | None:
    return SUPPORTED_CHAIN_ALIASES.get(label.strip().lower())


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_url(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not text.startswith(("http://", "https://")):
        text = f"https://{text}"
    return text


def _domain_from_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    hostname = parsed.hostname
    if not hostname:
        return None
    return hostname.removeprefix("www.")


def _twitter_url(value: Any) -> str | None:
    if not value:
        return None
    handle = str(value).strip().removeprefix("@")
    if not handle:
        return None
    if handle.startswith("http://") or handle.startswith("https://"):
        return handle
    return f"https://x.com/{handle}"
