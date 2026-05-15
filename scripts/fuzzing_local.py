from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from wr3_api.domain.enums import Chain, Tier  # noqa: E402
from wr3_api.domain.schemas import CreateAuditRequest  # noqa: E402
from wr3_api.services.audit_service import AuditService  # noqa: E402
from wr3_api.services.tools import ToolStatusService  # noqa: E402


async def run_cases(fixture_path: Path) -> dict[str, Any]:
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    service = AuditService()
    results = []
    started = time.perf_counter()
    for case in cases:
        record = await service.create_audit(
            CreateAuditRequest(
                chain=Chain(case["chain"]),
                address=case["address"],
                source=case["source"],
                requested_depth=case.get("requested_depth", "deep"),
                tier=Tier(case.get("tier", "team")),
                visibility="private",
                user_intent="pre_launch_self_check",
            )
        )
        await service.process_audit(record.audit_id)
        record = service.get_record(record.audit_id)
        fuzz_runs = [run for run in record.engine_runs if run.engine == "ai_fuzzing"]
        latest = fuzz_runs[-1] if fuzz_runs else None
        results.append(
            {
                "id": case["id"],
                "audit_id": str(record.audit_id),
                "state": record.state,
                "fuzzing_status": latest.status if latest else "missing",
                "fuzzing_error": latest.error if latest else "missing_fuzzing_run",
                "artifact_uri": latest.artifact_uri if latest else None,
                "limitations": record.limitations,
            }
        )
    return {
        "kind": "fuzzing_local",
        "created_at": datetime.now(UTC).isoformat(),
        "duration_seconds": round(time.perf_counter() - started, 4),
        "fixture_path": str(fixture_path),
        "tool_status": ToolStatusService().summary(),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run wr3 local fuzzing fixture pass.")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "benchmarks/fixtures/fuzzing_cases.json")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/fuzzing/local-fuzzing-report.json")
    args = parser.parse_args()

    report = asyncio.run(run_cases(args.fixtures))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
