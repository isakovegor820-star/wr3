from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from wr3_api.domain.schemas import ProxyInfo, SourceMetadata

EIP1967_IMPLEMENTATION_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
EIP1967_ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
EVM_ADDRESS_RE = re.compile(r"0x[a-fA-F0-9]{40}")


def source_hash(source: str | None) -> str | None:
    if source is None:
        return None
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def build_source_metadata(
    *,
    source: str | None,
    origin: str,
    verified_at: datetime | None = None,
    explorer_url: str | None = None,
    explorer_metadata: dict[str, Any] | None = None,
    bytecode_only: bool = False,
) -> SourceMetadata:
    metadata = SourceMetadata(
        source_hash=source_hash(source),
        source_origin=origin,
        verified_at=verified_at,
        explorer_url=explorer_url,
        explorer_metadata=explorer_metadata or {},
        bytecode_only=bytecode_only,
        proxy_info=detect_proxy_info(source or "", explorer_metadata or {}),
    )
    if bytecode_only:
        metadata.proxy_info.limitations.append("proxy_detection_limited_without_verified_source")
    return metadata


def detect_proxy_info(source: str, explorer_metadata: dict[str, Any] | None = None) -> ProxyInfo:
    explorer_metadata = explorer_metadata or {}
    lower = source.lower()
    detection_sources: list[str] = []
    proxy_type: str | None = None

    if str(explorer_metadata.get("Proxy") or "").strip() == "1":
        detection_sources.append("explorer_proxy_flag")
        proxy_type = "explorer_proxy"
    if EIP1967_IMPLEMENTATION_SLOT.lower() in lower or "eip1967.proxy.implementation" in lower:
        detection_sources.append("eip1967_implementation_slot")
        proxy_type = "eip1967"
    if EIP1967_ADMIN_SLOT.lower() in lower or "eip1967.proxy.admin" in lower:
        detection_sources.append("eip1967_admin_slot")
        proxy_type = proxy_type or "eip1967"
    if "transparentupgradeableproxy" in lower:
        detection_sources.append("transparent_upgradeable_proxy_symbol")
        proxy_type = "transparent"
    if "erc1967proxy" in lower:
        detection_sources.append("erc1967_proxy_symbol")
        proxy_type = "eip1967"
    if "uupsupgradeable" in lower:
        detection_sources.append("uups_symbol")
        proxy_type = "uups"
    if "proxyadmin" in lower:
        detection_sources.append("proxy_admin_symbol")
    implementation_address = _first_address(str(explorer_metadata.get("Implementation") or ""))
    admin_address = _first_address(str(explorer_metadata.get("Admin") or ""))
    owner_hint = _owner_hint(lower)
    is_proxy = bool(detection_sources or implementation_address)
    limitations: list[str] = []
    if is_proxy and not admin_address:
        limitations.append("proxy_admin_owner_extraction_requires_rpc_or_explorer_metadata")
    return ProxyInfo(
        is_proxy=is_proxy,
        proxy_type=proxy_type,
        implementation_address=implementation_address,
        admin_address=admin_address,
        owner_hint=owner_hint,
        eoa_admin_possible=is_proxy and bool(owner_hint in {"owner_function", "only_owner"}),
        detection_sources=detection_sources,
        limitations=limitations,
    )


def _first_address(value: str) -> str | None:
    match = EVM_ADDRESS_RE.search(value)
    return match.group(0) if match else None


def _owner_hint(lower_source: str) -> str | None:
    if "onlyowner" in lower_source:
        return "only_owner"
    if re.search(r"function\s+owner\s*\(", lower_source):
        return "owner_function"
    if re.search(r"function\s+admin\s*\(", lower_source):
        return "admin_function"
    return None
