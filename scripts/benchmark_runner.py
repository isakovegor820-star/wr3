from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from wr3_api.main import create_app  # noqa: E402


def wait_for_terminal(client: TestClient, audit_id: str, owner_token: str) -> dict[str, Any]:
    payload: dict[str, Any] | None = None
    for _ in range(10):
        response = client.get(f"/v1/audits/{audit_id}", params={"owner_token": owner_token})
        response.raise_for_status()
        payload = response.json()
        if payload["state"] in {"completed", "needs_source", "partial", "failed"}:
            return payload
    if payload is None:
        raise RuntimeError("audit status was never loaded")
    raise RuntimeError(f"audit did not reach terminal MVP state: {payload['state']}")


def run_fixture_cases(fixture_path: Path) -> dict[str, Any]:
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    client = TestClient(create_app())
    results: list[dict[str, Any]] = []
    expected_total = 0
    detected_total = 0
    false_positive_total = 0
    successful_cases = 0
    total_time_to_report = 0.0
    attempted_poc_total = 0
    confirmed_poc_total = 0

    for case in cases:
        started = time.perf_counter()
        response = client.post(
            "/v1/audits",
            json={
                "chain": case["chain"],
                "address": case["address"],
                "source": case["source"],
                "requested_depth": "preliminary",
                "visibility": "private",
                "user_intent": "pre_launch_self_check",
            },
        )
        response.raise_for_status()
        create_payload = response.json()
        audit_id = create_payload["audit_id"]
        wait_for_terminal(client, audit_id, create_payload["owner_access_token"])
        findings_response = client.get(
            f"/v1/audits/{audit_id}/findings",
            params={"owner_token": create_payload["owner_access_token"]},
        )
        findings_response.raise_for_status()
        findings = findings_response.json()
        elapsed = time.perf_counter() - started
        total_time_to_report += elapsed
        detected_categories = {
            finding["taxonomy"]["wr3_category"]
            for finding in findings
            if finding["exploitability"] != "dismissed"
            and finding["taxonomy"]["wr3_category"] != "informational"
        }
        attempted_poc = sum(
            1
            for finding in findings
            if finding.get("evidence", {}).get("poc_status") not in {None, "not_attempted"}
        )
        confirmed_poc = sum(
            1
            for finding in findings
            if finding.get("evidence", {}).get("poc_status") == "confirmed"
        )
        attempted_poc_total += attempted_poc
        confirmed_poc_total += confirmed_poc
        expected_categories = set(case.get("expected_categories", []))
        expected_total += len(expected_categories)
        detected = sorted(expected_categories & detected_categories)
        detected_total += len(detected)
        false_positive_total += len(detected_categories - expected_categories)
        if expected_categories.issubset(detected_categories):
            successful_cases += 1
        results.append(
            {
                "id": case["id"],
                "audit_id": audit_id,
                "expected_categories": sorted(expected_categories),
                "detected_categories": sorted(detected_categories),
                "matched_categories": detected,
                "passed": expected_categories.issubset(detected_categories),
                "time_to_report_seconds": round(elapsed, 4),
                "poc_attempted_count": attempted_poc,
                "poc_confirmed_count": confirmed_poc,
            }
        )

    recall = detected_total / expected_total if expected_total else 1.0
    precision_denominator = detected_total + false_positive_total
    precision = detected_total / precision_denominator if precision_denominator else 1.0
    poc_confirmation_rate = confirmed_poc_total / attempted_poc_total if attempted_poc_total else 0.0
    avg_time_to_report = total_time_to_report / len(cases) if cases else 0.0
    return {
        "dataset": str(fixture_path),
        "dataset_kind": fixture_path.stem,
        "created_at": datetime.now(UTC).isoformat(),
        "case_count": len(cases),
        "successful_cases": successful_cases,
        "case_success_rate": successful_cases / len(cases) if cases else 0,
        "expected_category_count": expected_total,
        "detected_expected_category_count": detected_total,
        "false_positive_category_count": false_positive_total,
        "recall": recall,
        "precision": precision,
        "fp_reduction": None,
        "poc_confirmation_rate": poc_confirmation_rate,
        "time_to_report_seconds_avg": avg_time_to_report,
        "cost_to_report_usd_estimated": 0.0,
        "cost_model": "local_testclient_no_provider_calls",
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run wr3 local benchmark fixture set.")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=ROOT / "benchmarks" / "fixtures" / "mvp_cases.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts" / "benchmarks" / "mvp-metrics.json",
    )
    args = parser.parse_args()

    metrics = run_fixture_cases(args.fixtures)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
