from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external" / "benchmarks"
OUT_DIR = ROOT / "artifacts" / "benchmarks"
SUBSET_DIR = ROOT / "benchmarks" / "subsets"


@dataclass(frozen=True)
class CuratedCase:
    id: str
    dataset: str
    chain: str
    path: str
    content_hash: str
    category: str
    expected_signal: str
    safe_use: str


def sha256_file(path: Path, max_bytes: int = 1_000_000) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        digest.update(handle.read(max_bytes))
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def git_sha(path: Path) -> str | None:
    head = path / ".git" / "HEAD"
    if not head.exists():
        return None
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        timeout=8,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def pick_smartbugs(limit_per_category: int = 6) -> list[CuratedCase]:
    root = EXTERNAL / "smartbugs-curated" / "dataset"
    if not root.exists():
        return []
    cases: list[CuratedCase] = []
    preferred = [
        "reentrancy",
        "access_control",
        "unchecked_low_level_calls",
        "arithmetic",
        "bad_randomness",
        "denial_of_service",
    ]
    categories = [root / name for name in preferred if (root / name).exists()]
    categories.extend(path for path in sorted(root.iterdir()) if path.is_dir() and path.name not in preferred)
    for category_dir in categories:
        selected = sorted(category_dir.glob("*.sol"))[:limit_per_category]
        for path in selected:
            cases.append(
                CuratedCase(
                    id=f"smartbugs-{category_dir.name}-{path.stem}",
                    dataset="smartbugs-curated",
                    chain="evm",
                    path=rel(path),
                    content_hash=sha256_file(path),
                    category=category_dir.name,
                    expected_signal=category_dir.name,
                    safe_use="local_static_analysis_only",
                )
            )
    return cases


def pick_defihacklabs(limit: int = 60) -> list[CuratedCase]:
    root = EXTERNAL / "DeFiHackLabs" / "src" / "test"
    if not root.exists():
        return []
    cases: list[CuratedCase] = []
    files = [path for path in sorted(root.rglob("*.sol")) if "Exploit-template" not in path.name]
    for path in files[:limit]:
        date_part = path.parent.name
        cases.append(
            CuratedCase(
                id=f"defihacklabs-{date_part}-{path.stem}",
                dataset="DeFiHackLabs",
                chain="evm",
                path=rel(path),
                content_hash=sha256_file(path),
                category=date_part,
                expected_signal="historical_exploit_pattern",
                safe_use="read_only_benchmark_no_mainnet_execution",
            )
        )
    return cases


def pick_sealevel(limit: int = 40) -> list[CuratedCase]:
    root = EXTERNAL / "sealevel-attacks"
    if not root.exists():
        return []
    candidates = sorted(root.glob("programs/**/src/lib.rs"))
    if not candidates:
        candidates = sorted(root.rglob("*.rs"))
    cases: list[CuratedCase] = []
    for path in candidates[:limit]:
        parts = path.relative_to(root).parts
        category = parts[1] if len(parts) > 2 and parts[0] == "programs" else path.parent.name
        cases.append(
            CuratedCase(
                id=f"sealevel-{category}-{path.stem}",
                dataset="sealevel-attacks",
                chain="solana",
                path=rel(path),
                content_hash=sha256_file(path),
                category=category,
                expected_signal="solana_anchor_footgun",
                safe_use="local_static_analysis_or_test_validator_only",
            )
        )
    return cases


def write_subset(name: str, cases: list[CuratedCase]) -> str:
    SUBSET_DIR.mkdir(parents=True, exist_ok=True)
    path = SUBSET_DIR / f"{name}.json"
    payload = {
        "kind": "wr3_curated_benchmark_subset",
        "created_at": datetime.now(UTC).isoformat(),
        "case_count": len(cases),
        "cases": [asdict(case) for case in cases],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return rel(path)


def main() -> int:
    subsets = {
        "smartbugs_curated_subset": pick_smartbugs(),
        "defihacklabs_curated_subset": pick_defihacklabs(),
        "sealevel_attacks_curated_subset": pick_sealevel(),
    }
    all_cases = [case for cases in subsets.values() for case in cases]
    subset_paths = {name: write_subset(name, cases) for name, cases in subsets.items()}
    dataset_roots = {
        "DeFiHackLabs": EXTERNAL / "DeFiHackLabs",
        "smartbugs-curated": EXTERNAL / "smartbugs-curated",
        "sealevel-attacks": EXTERNAL / "sealevel-attacks",
    }
    payload = {
        "kind": "wr3_curated_benchmark_manifest",
        "created_at": datetime.now(UTC).isoformat(),
        "case_count": len(all_cases),
        "dataset_commits": {
            dataset: git_sha(path)
            for dataset, path in dataset_roots.items()
        },
        "subset_paths": subset_paths,
        "coverage": {
            dataset: len(cases)
            for dataset, cases in subsets.items()
        },
        "safety": [
            "Manifest stores paths and hashes, not copied exploit text.",
            "DeFiHackLabs cases are read-only benchmark metadata; do not execute mainnet exploit scripts.",
            "Solana cases are for local static analysis or test-validator only.",
        ],
        "cases": [asdict(case) for case in all_cases],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "curated-benchmark-manifest.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "cases"}, indent=2))
    return 0 if all_cases else 1


if __name__ == "__main__":
    raise SystemExit(main())
