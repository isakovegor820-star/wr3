from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from wr3_api.adapters.base import EngineRunOptions, NormalizedSource  # noqa: E402
from wr3_api.adapters.heuristic_evm import HeuristicEvmAdapter  # noqa: E402
from wr3_api.adapters.heuristic_solana import HeuristicSolanaAdapter  # noqa: E402
from wr3_api.domain.enums import Chain  # noqa: E402
from wr3_api.services.tools import ToolStatusService  # noqa: E402


SMARTBUGS_CATEGORY_MAP = {
    "reentrancy": {"reentrancy"},
    "access_control": {"access_control"},
    "unchecked_low_level_calls": {"reentrancy", "unchecked_low_level_calls"},
    "arithmetic": set(),
    "bad_randomness": set(),
    "denial_of_service": set(),
}


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def expected_categories(case: dict[str, Any]) -> set[str]:
    if case["dataset"] == "smartbugs-curated":
        return set(SMARTBUGS_CATEGORY_MAP.get(case["category"], set()))
    if case["dataset"] == "sealevel-attacks":
        return {"solana_account_validation", "solana_signer", "solana_pda", "solana_accounting"}
    return set()


async def run_case(case: dict[str, Any]) -> dict[str, Any]:
    source_path = ROOT / case["path"]
    source = source_path.read_text(encoding="utf-8", errors="replace")
    chain = Chain.SOLANA if case["chain"] == "solana" else Chain.ETHEREUM
    adapter = HeuristicSolanaAdapter() if chain == Chain.SOLANA else HeuristicEvmAdapter()
    normalized = NormalizedSource(
        chain=chain,
        address=None,
        source=source,
        contract_name=source_path.stem,
        file_name=case["path"],
    )
    started = time.perf_counter()
    result = await adapter.run(normalized, EngineRunOptions(audit_id=f"bench-{case['id']}", timeout_seconds=30))
    elapsed = time.perf_counter() - started
    detected = {
        finding.taxonomy.wr3_category
        for finding in result.findings
        if finding.taxonomy.wr3_category != "informational"
    }
    expected = expected_categories(case)
    if expected:
        if case["dataset"] == "sealevel-attacks":
            matched = detected & expected
            passed = bool(matched)
        else:
            matched = detected & expected
            passed = expected.issubset(detected)
        evaluable = True
    else:
        matched = set()
        passed = None
        evaluable = False
    return {
        "id": case["id"],
        "dataset": case["dataset"],
        "path": case["path"],
        "category": case["category"],
        "engine": result.engine,
        "engine_status": result.status,
        "detected_categories": sorted(detected),
        "expected_categories": sorted(expected),
        "matched_categories": sorted(matched),
        "evaluable": evaluable,
        "passed": passed,
        "finding_count": len(result.findings),
        "duration_ms": round(elapsed * 1000, 3),
    }


async def run_cases(cases: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    selected = cases[:limit] if limit else cases
    return [await run_case(case) for case in selected]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    evaluable = [result for result in results if result["evaluable"]]
    passed = [result for result in evaluable if result["passed"] is True]
    expected_total = sum(len(result["expected_categories"]) for result in evaluable)
    matched_total = sum(len(result["matched_categories"]) for result in evaluable)
    detected_total = sum(len(result["detected_categories"]) for result in evaluable)
    dataset_counts = Counter(result["dataset"] for result in results)
    dataset_passed = Counter(result["dataset"] for result in passed)
    return {
        "case_count": len(results),
        "evaluable_case_count": len(evaluable),
        "passed_evaluable_case_count": len(passed),
        "non_evaluable_case_count": len(results) - len(evaluable),
        "case_success_rate": len(passed) / len(evaluable) if evaluable else None,
        "category_recall": matched_total / expected_total if expected_total else None,
        "category_precision": matched_total / detected_total if detected_total else None,
        "dataset_counts": dict(dataset_counts),
        "dataset_passed_counts": dict(dataset_passed),
        "duration_ms_total": round(sum(result["duration_ms"] for result in results), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a safe local smoke benchmark on the curated external subset manifest.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "artifacts/benchmarks/curated-benchmark-manifest.json")
    parser.add_argument("--limit", type=int, default=0, help="Optional case limit; 0 means all curated cases.")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/benchmarks/curated-benchmark-run.json")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    started = time.perf_counter()
    results = asyncio.run(run_cases(manifest.get("cases", []), args.limit or None))
    summary = summarize(results)
    payload = {
        "kind": "wr3_curated_benchmark_run",
        "created_at": datetime.now(UTC).isoformat(),
        "manifest": str(args.manifest.relative_to(ROOT)),
        "dataset_commits": manifest.get("dataset_commits", {}),
        "tool_status": ToolStatusService().summary(),
        "duration_seconds": round(time.perf_counter() - started, 4),
        "quality_note": (
            "This is a local heuristic smoke benchmark over curated public corpora. "
            "It is not a public quality claim until static tools/LLM triage/PoC layers "
            "are run and manually reviewed."
        ),
        "summary": summary,
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "results"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
