from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "external" / "benchmarks"
ARTIFACT_PATH = ROOT / "artifacts" / "benchmarks" / "external-dataset-inventory.json"


@dataclass(frozen=True)
class DatasetInventory:
    id: str
    path: str
    present: bool
    commit_sha: str | None
    solidity_files: int
    rust_files: int
    json_files: int
    markdown_files: int
    notes: str


def git_sha(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        timeout=8,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def count_files(path: Path, suffix: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob(f"*{suffix}") if item.is_file())


def inventory_dataset(dataset_id: str, notes: str) -> DatasetInventory:
    path = DATASET_ROOT / dataset_id
    return DatasetInventory(
        id=dataset_id,
        path=str(path.relative_to(ROOT)),
        present=path.exists(),
        commit_sha=git_sha(path),
        solidity_files=count_files(path, ".sol"),
        rust_files=count_files(path, ".rs"),
        json_files=count_files(path, ".json"),
        markdown_files=count_files(path, ".md"),
        notes=notes,
    )


def main() -> int:
    datasets = [
        inventory_dataset(
            "DeFiHackLabs",
            "Public exploit PoC corpus; use only for local benchmarks and attribution-aware summaries.",
        ),
        inventory_dataset(
            "smartbugs-curated",
            "Curated vulnerable Solidity contracts for labeled static-analysis tests.",
        ),
        inventory_dataset(
            "sealevel-attacks",
            "Solana insecure/recommended examples for beta detector coverage.",
        ),
    ]
    payload = {
        "kind": "external_benchmark_inventory",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset_root": str(DATASET_ROOT.relative_to(ROOT)),
        "datasets": [asdict(dataset) for dataset in datasets],
        "all_present": all(dataset.present for dataset in datasets),
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["all_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
