from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external" / "benchmarks"
OUT = ROOT / "artifacts" / "rag" / "local-security-corpus.json"
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{3,}")


@dataclass(frozen=True)
class CorpusRecord:
    id: str
    source: str
    path: str
    title: str
    content_hash: str
    tags: list[str]
    token_count: int
    summary: str


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def read_text(path: Path, max_bytes: int = 80_000) -> str:
    raw = path.read_bytes()[:max_bytes]
    return raw.decode("utf-8", errors="replace")


def summarize(text: str, max_chars: int = 600) -> str:
    cleaned = " ".join(text.replace("\x00", " ").split())
    return cleaned[:max_chars]


def record_for(path: Path, source: str, tags: list[str]) -> CorpusRecord:
    text = read_text(path)
    content_hash = sha(text)
    title = path.stem.replace("_", " ").replace("-", " ")
    return CorpusRecord(
        id=f"wr3-local-rag-{content_hash[:16]}",
        source=source,
        path=str(path.relative_to(ROOT)),
        title=title,
        content_hash=content_hash,
        tags=tags,
        token_count=len(tokens(text)),
        summary=summarize(text),
    )


def collect_records() -> list[CorpusRecord]:
    records: list[CorpusRecord] = []
    dataset_specs = [
        ("DeFiHackLabs", ["defihacklabs", "evm", "exploit-poc"], {".sol", ".md"}),
        ("smartbugs-curated", ["smartbugs", "evm", "labeled-vulnerability"], {".sol", ".json", ".md"}),
        ("sealevel-attacks", ["sealevel-attacks", "solana", "anchor"], {".rs", ".md"}),
    ]
    for dataset, tags, suffixes in dataset_specs:
        root = EXTERNAL / dataset
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            if any(part in {".git", "node_modules", "target"} for part in path.parts):
                continue
            try:
                records.append(record_for(path, dataset, tags + [path.suffix.lower().lstrip(".")]))
            except OSError:
                continue
    return records


def main() -> int:
    records = collect_records()
    payload = {
        "kind": "local_security_rag_corpus",
        "created_at": datetime.now(UTC).isoformat(),
        "record_count": len(records),
        "sources": sorted({record.source for record in records}),
        "note": "Local metadata/summaries from public datasets. Do not paste long third-party audit text into public reports.",
        "records": [asdict(record) for record in records],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "records"}, indent=2))
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
