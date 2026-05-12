from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from wr3_api.domain.enums import Chain, Severity
from wr3_api.domain.schemas import utc_now
from wr3_api.services.rag import DeterministicEmbeddingProvider, cosine_similarity


AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([kKmMbB])?")


@dataclass(frozen=True)
class NewsSource:
    name: str
    url: str
    kind: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class NewsItem:
    id: str
    source: str
    title: str
    url: str | None
    summary: str
    chain: Chain | None = None
    severity: Severity = Severity.INFO
    category: str = "unknown"
    published_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


DEFAULT_NEWS_SOURCES: tuple[NewsSource, ...] = (
    NewsSource("rekt", "https://rekt.news", "rss", ("hacks", "postmortem")),
    NewsSource("defillama-hacks", "https://defillama.com/hacks", "api", ("hacks", "structured")),
    NewsSource("helius", "https://www.helius.dev/blog", "rss", ("solana", "postmortem")),
    NewsSource("peckshield", "https://x.com/PeckShieldAlert", "social", ("alerts",)),
    NewsSource("slowmist", "https://x.com/SlowMist_Team", "social", ("alerts",)),
    NewsSource("certik-alert", "https://x.com/CertiKAlert", "social", ("alerts",)),
)


class NewsDeduper:
    def __init__(self, *, threshold: float = 0.85) -> None:
        self.threshold = threshold
        self._embedder = DeterministicEmbeddingProvider()

    def dedupe(self, items: list[NewsItem]) -> list[NewsItem]:
        kept: list[NewsItem] = []
        kept_embeddings: list[tuple[float, ...]] = []
        seen_ids: set[str] = set()
        for item in items:
            if item.id in seen_ids:
                continue
            embedding = self._embedder.embed(f"{item.title}\n{item.summary}")
            if any(cosine_similarity(embedding, existing) >= self.threshold for existing in kept_embeddings):
                continue
            kept.append(item)
            kept_embeddings.append(embedding)
            seen_ids.add(item.id)
        return kept


def normalize_defillama_hack(raw: dict[str, Any]) -> NewsItem:
    title = str(raw.get("name") or raw.get("title") or "Unknown exploit")
    summary = str(raw.get("technique") or raw.get("description") or raw.get("classification") or "")
    chain = infer_chain(" ".join([title, summary, str(raw.get("chain") or "")]))
    amount = raw.get("amount") or raw.get("fundsLost") or raw.get("usdAmount")
    severity = infer_severity(str(amount or summary or title))
    category = infer_category(" ".join([title, summary]))
    url = raw.get("url") or raw.get("source") or raw.get("postMortem")
    published_at = parse_date(raw.get("date") or raw.get("timestamp"))
    stable = "|".join([title.lower(), str(url or ""), str(published_at.date())])
    return NewsItem(
        id=f"wr3-news-{hashlib.sha256(stable.encode('utf-8')).hexdigest()[:16]}",
        source="defillama-hacks",
        title=title,
        url=str(url) if url else None,
        summary=summary,
        chain=chain,
        severity=severity,
        category=category,
        published_at=published_at,
        metadata={"raw_amount": amount},
    )


def infer_chain(text: str) -> Chain | None:
    lowered = text.lower()
    if "solana" in lowered:
        return Chain.SOLANA
    if "base" in lowered:
        return Chain.BASE
    if "bsc" in lowered or "bnb" in lowered or "pancake" in lowered:
        return Chain.BSC
    if "arbitrum" in lowered:
        return Chain.ARBITRUM
    if "ethereum" in lowered or "mainnet" in lowered:
        return Chain.ETHEREUM
    return None


def infer_category(text: str) -> str:
    lowered = text.lower()
    if "reentr" in lowered:
        return "reentrancy"
    if "oracle" in lowered or "price" in lowered:
        return "oracle"
    if "private key" in lowered or "key compromise" in lowered:
        return "key_compromise"
    if "access control" in lowered or "owner" in lowered:
        return "access_control"
    if "bridge" in lowered:
        return "bridge"
    return "incident"


def infer_severity(text: str) -> Severity:
    lowered = text.lower()
    if "critical" in lowered:
        return Severity.CRITICAL
    match = AMOUNT_RE.search(lowered.replace(",", ""))
    if not match:
        return Severity.INFO
    amount = float(match.group(1))
    suffix = (match.group(2) or "").lower()
    multiplier = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(suffix, 1)
    usd = amount * multiplier
    if usd >= 10_000_000:
        return Severity.CRITICAL
    if usd >= 1_000_000:
        return Severity.HIGH
    if usd >= 100_000:
        return Severity.MEDIUM
    return Severity.LOW


def parse_date(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, int | float):
        if value > 10_000_000_000:
            value = value / 1000
        return datetime.fromtimestamp(value, tz=utc_now().tzinfo)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return utc_now()
    return utc_now()
