from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from wr3_api.domain.schemas import utc_now


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{3,}")


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    source: str
    title: str
    content_hash: str
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    document_id: str
    text: str
    token_count: int
    embedding: tuple[float, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RagSearchResult:
    document: KnowledgeDocument
    chunk: KnowledgeChunk
    score: float


class DeterministicEmbeddingProvider:
    """Small local embedding fallback for tests and offline MVP demos.

    Production embeddings are expected to use Gemini/OpenAI-compatible providers
    and store vectors through pgvector. This fallback is deterministic and never
    leaves the process, which keeps security test fixtures hermetic.
    """

    dimensions = 32

    def embed(self, text: str) -> tuple[float, ...]:
        buckets = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = digest[0] % self.dimensions
            buckets[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in buckets)) or 1.0
        return tuple(value / norm for value in buckets)


class LocalKnowledgeBase:
    def __init__(self, embedding_provider: DeterministicEmbeddingProvider | None = None) -> None:
        self._embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self._documents: dict[str, KnowledgeDocument] = {}
        self._chunks: dict[str, KnowledgeChunk] = {}

    def ingest(
        self,
        *,
        source: str,
        title: str,
        content: str,
        tags: list[str] | tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeDocument:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        document_id = f"wr3-kb-{content_hash[:16]}"
        document = KnowledgeDocument(
            id=document_id,
            source=source,
            title=title,
            content_hash=content_hash,
            tags=tuple(sorted(set(tags))),
            metadata=metadata or {},
        )
        self._documents[document_id] = document
        for index, chunk_text in enumerate(chunk_text_content(content)):
            chunk_id = f"{document_id}-{index}"
            self._chunks[chunk_id] = KnowledgeChunk(
                id=chunk_id,
                document_id=document_id,
                text=chunk_text,
                token_count=len(tokenize(chunk_text)),
                embedding=self._embedding_provider.embed(chunk_text),
                metadata={"chunk_index": index},
            )
        return document

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        tags: list[str] | tuple[str, ...] | None = None,
    ) -> list[RagSearchResult]:
        query_embedding = self._embedding_provider.embed(query)
        required_tags = set(tags or [])
        results: list[RagSearchResult] = []
        for chunk in self._chunks.values():
            document = self._documents[chunk.document_id]
            if required_tags and not required_tags.issubset(set(document.tags)):
                continue
            score = cosine_similarity(query_embedding, chunk.embedding)
            if score <= 0:
                continue
            results.append(RagSearchResult(document=document, chunk=chunk, score=score))
        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(token.lower() for token in TOKEN_RE.findall(text))


def chunk_text_content(content: str, *, max_tokens: int = 180) -> list[str]:
    tokens = tokenize(content)
    if not tokens:
        return [content[:1000]]
    chunks: list[str] = []
    words = content.split()
    current: list[str] = []
    current_tokens = 0
    for word in words:
        current.append(word)
        current_tokens += len(tokenize(word))
        if current_tokens >= max_tokens:
            chunks.append(" ".join(current))
            current = []
            current_tokens = 0
    if current:
        chunks.append(" ".join(current))
    return chunks or [content[:1000]]


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))
