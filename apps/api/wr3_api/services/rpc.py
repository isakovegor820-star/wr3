from __future__ import annotations

from dataclasses import dataclass

import httpx

from wr3_api.core.config import Settings, get_settings
from wr3_api.domain.enums import Chain


PUBLIC_RPC_URLS: dict[Chain, str] = {
    Chain.ETHEREUM: "https://ethereum-rpc.publicnode.com",
    Chain.BASE: "https://base-rpc.publicnode.com",
    Chain.BSC: "https://bsc-rpc.publicnode.com",
    Chain.ARBITRUM: "https://arbitrum-one-rpc.publicnode.com",
    Chain.SOLANA: "https://solana-rpc.publicnode.com",
}


@dataclass(frozen=True)
class RpcEndpoint:
    chain: Chain
    url: str | None
    source: str
    configured: bool
    free_fallback: bool


class RpcRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def endpoint_for(self, chain: Chain) -> RpcEndpoint:
        configured = {
            Chain.ETHEREUM: self._settings.ethereum_rpc_url,
            Chain.BASE: self._settings.base_rpc_url,
            Chain.BSC: self._settings.bsc_rpc_url,
            Chain.ARBITRUM: self._settings.arbitrum_rpc_url,
            Chain.SOLANA: self._settings.solana_rpc_url or self._settings.helius_rpc_url,
        }.get(chain)
        if configured:
            return RpcEndpoint(chain=chain, url=configured, source="env", configured=True, free_fallback=False)
        if self._settings.public_rpc_fallback_enabled:
            return RpcEndpoint(
                chain=chain,
                url=PUBLIC_RPC_URLS.get(chain),
                source="publicnode",
                configured=True,
                free_fallback=True,
            )
        return RpcEndpoint(chain=chain, url=None, source="disabled", configured=False, free_fallback=False)

    def summary(self) -> list[dict[str, object]]:
        return [
            {
                "chain": chain,
                "configured": (endpoint := self.endpoint_for(chain)).configured,
                "source": endpoint.source,
                "free_fallback": endpoint.free_fallback,
                "url_host": _host_only(endpoint.url),
            }
            for chain in Chain
        ]

    async def json_rpc(self, chain: Chain, method: str, params: list[object]) -> dict[str, object]:
        endpoint = self.endpoint_for(chain)
        if not endpoint.url:
            raise RuntimeError(f"rpc_endpoint_missing:{chain}")
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                endpoint.url,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            )
            response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("rpc_json_object_required")
        return payload


def _host_only(url: str | None) -> str | None:
    if not url:
        return None
    return url.split("//", 1)[-1].split("/", 1)[0].split("@")[-1]
