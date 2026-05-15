from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_runner import run_fixture_cases  # noqa: E402

API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from wr3_api.services.tools import ToolStatusService  # noqa: E402


DATASETS = (
    ROOT / "benchmarks/fixtures/defihacklabs_sample.json",
    ROOT / "benchmarks/fixtures/mvp_cases.json",
    ROOT / "benchmarks/fixtures/smartbugs_sample.json",
    ROOT / "benchmarks/fixtures/sealevel_attacks_sample.json",
)


def main() -> int:
    started = time.perf_counter()
    dataset_reports: list[dict[str, Any]] = []
    hard_failures: list[dict[str, str]] = []

    for fixture_path in DATASETS:
        try:
            report = run_fixture_cases(fixture_path)
            report["status"] = "passed"
            dataset_reports.append(report)
        except Exception as exc:  # keep local benchmark useful when one dataset breaks
            hard_failures.append(
                {
                    "dataset": str(fixture_path),
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                }
            )

    total_cases = sum(report.get("case_count", 0) for report in dataset_reports)
    successful_cases = sum(report.get("successful_cases", 0) for report in dataset_reports)
    expected_categories = sum(report.get("expected_category_count", 0) for report in dataset_reports)
    detected_expected = sum(report.get("detected_expected_category_count", 0) for report in dataset_reports)
    false_positive_categories = sum(report.get("false_positive_category_count", 0) for report in dataset_reports)
    precision_denominator = detected_expected + false_positive_categories

    aggregate = {
        "kind": "benchmark_local",
        "created_at": datetime.now(UTC).isoformat(),
        "duration_seconds": round(time.perf_counter() - started, 4),
        "artifact_path": "artifacts/benchmarks/local-benchmark-report.json",
        "tool_status": ToolStatusService().summary(),
        "summary": {
            "dataset_count": len(DATASETS),
            "datasets_passed": len(dataset_reports),
            "datasets_failed": len(hard_failures),
            "total_cases": total_cases,
            "successful_cases": successful_cases,
            "failed_cases": max(total_cases - successful_cases, 0),
            "skipped_cases": 0,
            "recall": detected_expected / expected_categories if expected_categories else 1.0,
            "precision": detected_expected / precision_denominator if precision_denominator else 1.0,
            "fp_reduction": None,
            "poc_confirmation_rate": 0.0,
            "cost_to_report_usd_estimated": 0.0,
        },
        "datasets": dataset_reports,
        "hard_failures": hard_failures,
    }

    out = ROOT / "artifacts/benchmarks/local-benchmark-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in aggregate.items() if k != "datasets"}, indent=2))
    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
