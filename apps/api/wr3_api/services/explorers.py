from __future__ import annotations

import json
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from typing import Any

import httpx

from wr3_api.core.config import Settings, get_settings
from wr3_api.domain.enums import Chain


@dataclass(frozen=True)
class ExplorerSourceResult:
    status: str
    source: str | None = None
    contract_name: str | None = None
    file_name: str | None = None
    reason: str | None = None
    explorer_url: str | None = None
    verified_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class ExplorerSourcePuller:
    name: str

    def supports(self, chain: Chain) -> bool:
        raise NotImplementedError

    async def pull(self, *, chain: Chain, address: str) -> ExplorerSourceResult:
        raise NotImplementedError


class EtherscanFamilySourcePuller(ExplorerSourcePuller):
    name = "etherscan_family"

    def __init__(self, settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._settings = settings or get_settings()
        self._transport = transport
        self._explorers = {
            Chain.ETHEREUM: ("https://api.etherscan.io/api", self._settings.etherscan_api_key, "etherscan"),
            Chain.BASE: ("https://api.basescan.org/api", self._settings.basescan_api_key, "basescan"),
            Chain.BSC: ("https://api.bscscan.com/api", self._settings.bscscan_api_key, "bscscan"),
            Chain.ARBITRUM: ("https://api.arbiscan.io/api", self._settings.arbiscan_api_key, "arbiscan"),
        }

    def supports(self, chain: Chain) -> bool:
        return chain in self._explorers

    async def pull(self, *, chain: Chain, address: str) -> ExplorerSourceResult:
        if chain not in self._explorers:
            return ExplorerSourceResult(status="unsupported", reason=f"{chain} explorer not configured")
        base_url, api_key, label = self._explorers[chain]
        if not api_key:
            return ExplorerSourceResult(status="missing", reason=f"{label}_api_key_missing")

        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": api_key,
        }
        last_error: str | None = None
        max_attempts = max(1, self._settings.explorer_max_retries + 1)
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(
                    timeout=self._settings.explorer_timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = await client.get(base_url, params=params)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        last_error = f"{label}_retryable_status:{response.status_code}"
                        if attempt < max_attempts - 1:
                            await self._sleep_before_retry()
                            continue
                    response.raise_for_status()
                    break
            except httpx.TimeoutException:
                last_error = f"{label}_timeout"
                if attempt < max_attempts - 1:
                    await self._sleep_before_retry()
                    continue
                return ExplorerSourceResult(status="rate_limited", reason=last_error)
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code == 429:
                    return ExplorerSourceResult(status="rate_limited", reason=last_error or f"{label}_rate_limited")
                return ExplorerSourceResult(status="failed", reason=f"{label}_http_status:{status_code}")
            except httpx.HTTPError as exc:
                return ExplorerSourceResult(status="failed", reason=f"{label}_http_error:{exc.__class__.__name__}")
        else:
            return ExplorerSourceResult(status="failed", reason=last_error or f"{label}_unknown_http_error")

        return parse_etherscan_source_payload(response, label=label, address=address)

    async def _sleep_before_retry(self) -> None:
        if self._settings.explorer_retry_backoff_seconds > 0:
            await asyncio.sleep(self._settings.explorer_retry_backoff_seconds)


class EtherscanV2SourcePuller(ExplorerSourcePuller):
    name = "etherscan_v2"

    chain_ids: dict[Chain, str] = {
        Chain.ETHEREUM: "1",
        Chain.BASE: "8453",
        Chain.BSC: "56",
        Chain.ARBITRUM: "42161",
    }

    def __init__(self, settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._settings = settings or get_settings()
        self._transport = transport

    def supports(self, chain: Chain) -> bool:
        return chain in self.chain_ids

    async def pull(self, *, chain: Chain, address: str) -> ExplorerSourceResult:
        if not self._settings.etherscan_v2_enabled:
            return ExplorerSourceResult(status="disabled", reason="etherscan_v2_disabled")
        if chain not in self.chain_ids:
            return ExplorerSourceResult(status="unsupported", reason=f"{chain} not supported by etherscan_v2")
        if not self._settings.etherscan_api_key:
            return ExplorerSourceResult(status="missing", reason="etherscan_v2_api_key_missing")

        params = {
            "chainid": self.chain_ids[chain],
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": self._settings.etherscan_api_key,
        }
        last_error: str | None = None
        max_attempts = max(1, self._settings.explorer_max_retries + 1)
        label = f"etherscan_v2:{chain}"
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(
                    timeout=self._settings.explorer_timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = await client.get(self._settings.etherscan_v2_base_url, params=params)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        last_error = f"{label}_retryable_status:{response.status_code}"
                        if attempt < max_attempts - 1:
                            await self._sleep_before_retry()
                            continue
                    response.raise_for_status()
                    break
            except httpx.TimeoutException:
                last_error = f"{label}_timeout"
                if attempt < max_attempts - 1:
                    await self._sleep_before_retry()
                    continue
                return ExplorerSourceResult(status="rate_limited", reason=last_error)
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code == 429:
                    return ExplorerSourceResult(status="rate_limited", reason=last_error or f"{label}_rate_limited")
                return ExplorerSourceResult(status="failed", reason=f"{label}_http_status:{status_code}")
            except httpx.HTTPError as exc:
                return ExplorerSourceResult(status="failed", reason=f"{label}_http_error:{exc.__class__.__name__}")
        else:
            return ExplorerSourceResult(status="failed", reason=last_error or f"{label}_unknown_http_error")
        return parse_etherscan_source_payload(response, label=label, address=address)

    async def _sleep_before_retry(self) -> None:
        if self._settings.explorer_retry_backoff_seconds > 0:
            await asyncio.sleep(self._settings.explorer_retry_backoff_seconds)


def parse_etherscan_source_payload(response: httpx.Response, *, label: str, address: str) -> ExplorerSourceResult:
    try:
        payload = response.json()
    except ValueError:
        return ExplorerSourceResult(status="failed", reason=f"{label}_invalid_json")
    result = payload.get("result")
    if isinstance(result, str) and payload.get("status") == "0":
        lowered = result.lower()
        if "rate limit" in lowered or "max rate" in lowered:
            return ExplorerSourceResult(status="rate_limited", reason=f"{label}_rate_limited")
        return ExplorerSourceResult(status="missing", reason=f"{label}:{result[:120]}")
    if not isinstance(result, list) or not result:
        return ExplorerSourceResult(status="missing", reason=f"{label}_no_source_result")
    first = result[0]
    source_code = unescape(str(first.get("SourceCode") or "")).strip()
    if not source_code:
        return ExplorerSourceResult(status="missing", reason=f"{label}_source_not_verified")
    contract_name = str(first.get("ContractName") or "Contract")
    metadata = {
        key: first.get(key)
        for key in (
            "CompilerVersion",
            "OptimizationUsed",
            "Runs",
            "ConstructorArguments",
            "EVMVersion",
            "LicenseType",
            "Proxy",
            "Implementation",
            "Admin",
            "SwarmSource",
        )
        if first.get(key) not in {None, ""}
    }
    return ExplorerSourceResult(
        status="verified",
        source=_unwrap_explorer_source(source_code),
        contract_name=contract_name,
        file_name="Contract.sol",
        explorer_url=f"{label}:{address}",
        verified_at=datetime.now(UTC),
        metadata=metadata,
    )


def default_explorer_pullers() -> list[ExplorerSourcePuller]:
    return [EtherscanV2SourcePuller(), EtherscanFamilySourcePuller()]


def _unwrap_explorer_source(source_code: str) -> str:
    # Etherscan-family explorers sometimes wrap standard-json input in double
    # braces.
    if source_code.startswith("{{") and source_code.endswith("}}"):
        source_code = source_code[1:-1]
    if source_code.startswith("{"):
        try:
            payload = json.loads(source_code)
        except json.JSONDecodeError:
            return source_code
        sources = payload.get("sources") if isinstance(payload, dict) else None
        if isinstance(sources, dict):
            parts: list[str] = []
            for file_name, source_entry in sorted(sources.items()):
                if isinstance(source_entry, dict) and isinstance(source_entry.get("content"), str):
                    parts.append(f"// file: {file_name}\n{source_entry['content']}")
            if parts:
                return "\n\n".join(parts)
    return source_code
