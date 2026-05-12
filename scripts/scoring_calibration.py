from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_runner import run_fixture_cases  # noqa: E402


DEFAULT_FIXTURES = [
    ROOT / "benchmarks" / "fixtures" / "mvp_cases.json",
    ROOT / "benchmarks" / "fixtures" / "smartbugs_sample.json",
    ROOT / "benchmarks" / "fixtures" / "sealevel_attacks_sample.json",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run wr3 scoring calibration fixture sets.")
    parser.add_argument("--fixtures", type=Path, action="append", default=None)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts" / "benchmarks" / "scoring-calibration.json",
    )
    args = parser.parse_args()

    fixtures = args.fixtures or DEFAULT_FIXTURES
    runs = [run_fixture_cases(path) for path in fixtures]
    summary = {
        "created_at": datetime.now(UTC).isoformat(),
        "score_version": "wr3-score-v0.1",
        "run_count": len(runs),
        "case_count": sum(run["case_count"] for run in runs),
        "mean_recall": mean(run["recall"] for run in runs) if runs else 0.0,
        "mean_precision": mean(run["precision"] for run in runs) if runs else 0.0,
        "mean_time_to_report_seconds": mean(run["time_to_report_seconds_avg"] for run in runs)
        if runs
        else 0.0,
        "poc_confirmation_rate": mean(run["poc_confirmation_rate"] for run in runs) if runs else 0.0,
        "cost_to_report_usd_estimated": sum(run["cost_to_report_usd_estimated"] for run in runs),
        "limitations": [
            "sample_fixture_calibration_only",
            "replace_with_30_known_vulnerable_and_30_known_clean_cases_before_public_claims",
        ],
        "runs": runs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "runs"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
