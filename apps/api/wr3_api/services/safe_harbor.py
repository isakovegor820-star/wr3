from __future__ import annotations

import json
from pathlib import Path

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain


class SafeHarborRegistry:
    def __init__(self, entries: set[tuple[Chain, str]] | None = None) -> None:
        self._entries = entries if entries is not None else self._load_entries()

    def is_registered(self, chain: Chain, address: str | None) -> bool:
        if not address:
            return False
        return (chain, address.lower()) in self._entries

    def _load_entries(self) -> set[tuple[Chain, str]]:
        settings = get_settings()
        raw = settings.safe_harbor_registry_json
        if not raw and settings.safe_harbor_registry_path:
            path = Path(settings.safe_harbor_registry_path)
            if path.exists():
                raw = path.read_text(encoding="utf-8")
        if not raw:
            return set()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return set()
        rows = parsed.get("contracts", parsed) if isinstance(parsed, dict) else parsed
        entries: set[tuple[Chain, str]] = set()
        if not isinstance(rows, list):
            return entries
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                chain = Chain(str(row.get("chain", "")).lower())
            except ValueError:
                continue
            address = str(row.get("address") or "").strip().lower()
            if address:
                entries.add((chain, address))
        return entries
