from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from wr3_api.services.sandbox import SandboxPolicy  # noqa: E402


@dataclass(frozen=True)
class EvidenceCheck:
    id: str
    status: str
    evidence: str


def run_entrypoint_with_env(env_name: str) -> EvidenceCheck:
    script = ROOT / "infra" / "sandbox" / "entrypoint.sh"
    result = subprocess.run(
        ["bash", str(script), "true"],
        check=False,
        capture_output=True,
        text=True,
        timeout=8,
        env={env_name: "sentinel"},
    )
    ok = result.returncode == 64 and "refusing to start sandbox" in result.stderr
    return EvidenceCheck(
        id=f"entrypoint_refuses_{env_name.lower()}",
        status="passed" if ok else "failed",
        evidence=f"returncode={result.returncode}; stderr={result.stderr.strip()}",
    )


def policy_checks() -> list[EvidenceCheck]:
    policy = SandboxPolicy(allowed_rpc_hosts=["127.0.0.1", "localhost", "base-mainnet.g.alchemy.com"])
    cases = [
        ("allow_forge_json", policy.validate_argv(["forge", "test", "--json"]).allowed, "forge test --json"),
        ("deny_shell_metachar", not policy.validate_command_string("forge test; curl https://example.com").allowed, "shell metacharacters"),
        ("deny_curl", not policy.validate_argv(["curl", "https://example.com"]).allowed, "curl binary"),
        ("deny_private_key", not policy.validate_argv(["forge", "test", "--private-key", "0xabc"]).allowed, "private key flag"),
        (
            "allow_rpc_allowlist",
            policy.validate_argv(["forge", "test", "--fork-url", "https://base-mainnet.g.alchemy.com/v2/demo"]).allowed,
            "allowlisted fork RPC",
        ),
        (
            "deny_rpc_not_allowlisted",
            not policy.validate_argv(["forge", "test", "--fork-url", "https://evil.example/rpc"]).allowed,
            "non-allowlisted fork RPC",
        ),
    ]
    return [
        EvidenceCheck(id=case_id, status="passed" if ok else "failed", evidence=evidence)
        for case_id, ok, evidence in cases
    ]


def main() -> int:
    checks = [
        *policy_checks(),
        run_entrypoint_with_env("WR3_DATABASE_URL"),
        run_entrypoint_with_env("DOPPLER_TOKEN"),
        run_entrypoint_with_env("OP_SERVICE_ACCOUNT_TOKEN"),
    ]
    passed = sum(check.status == "passed" for check in checks)
    failed = len(checks) - passed
    payload = {
        "kind": "wr3_sandbox_evidence",
        "created_at": datetime.now(UTC).isoformat(),
        "passed": passed,
        "failed": failed,
        "production_note": "This is local evidence for policy and secret isolation. A real container/VM egress test is still required before public launch.",
        "checks": [asdict(check) for check in checks],
    }
    out_dir = ROOT / "artifacts" / "readiness"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"sandbox_evidence_{stamp}.json"
    md_path = out_dir / f"sandbox_evidence_{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# wr3 Sandbox Evidence",
                "",
                f"- Created: {payload['created_at']}",
                f"- Passed: {passed}",
                f"- Failed: {failed}",
                f"- Note: {payload['production_note']}",
                "",
                "| Check | Status | Evidence |",
                "| --- | --- | --- |",
                *[
                    f"| {check.id} | {check.status} | {check.evidence.replace('|', '/')} |"
                    for check in checks
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "checks"}, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
