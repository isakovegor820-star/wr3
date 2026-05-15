from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "artifacts" / "readiness"
IMAGE = "wr3-sandbox:local-evidence"


@dataclass(frozen=True)
class ContainerCheck:
    id: str
    status: str
    evidence: str
    next_step: str


def run(command: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
    except Exception as exc:
        return 999, f"{exc.__class__.__name__}: {exc}"
    output = (result.stdout + result.stderr).strip()
    return result.returncode, output[:1000]


def main() -> int:
    checks: list[ContainerCheck] = []
    if shutil.which("docker") is None:
        checks.append(
            ContainerCheck(
                "docker_available",
                "blocked",
                "docker cli missing",
                "Install/start Docker or run this check on the staging sandbox host.",
            )
        )
    else:
        code, output = run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=10)
        if code != 0:
            checks.append(
                ContainerCheck(
                    "docker_daemon",
                    "blocked",
                    output or "docker daemon unavailable",
                    "Start Docker Desktop or run on the sandbox host.",
                )
            )
        else:
            checks.append(ContainerCheck("docker_daemon", "done", f"Docker server {output}", "No action."))
            build_code, build_output = run(["docker", "build", "-f", "infra/sandbox/Dockerfile", "-t", IMAGE, "."], timeout=180)
            checks.append(
                ContainerCheck(
                    "sandbox_image_build",
                    "done" if build_code == 0 else "blocked",
                    "image built" if build_code == 0 else build_output,
                    "Fix Dockerfile or build on staging host.",
                )
            )
            if build_code == 0:
                for env_name, env_value in [
                    ("WR3_DATABASE_URL", "postgresql://prod"),
                    ("DOPPLER_TOKEN", "secret"),
                    ("OP_SERVICE_ACCOUNT_TOKEN", "secret"),
                ]:
                    code, output = run(["docker", "run", "--rm", "-e", f"{env_name}={env_value}", IMAGE, "true"], timeout=20)
                    checks.append(
                        ContainerCheck(
                            f"reject_{env_name.lower()}",
                            "done" if code == 64 and "refusing to start sandbox" in output else "blocked",
                            f"exit={code}; {output}",
                            "Entry point must reject DB and secret-manager credentials.",
                        )
                    )
                code, output = run(["docker", "run", "--rm", "--network", "none", IMAGE, "true"], timeout=20)
                checks.append(
                    ContainerCheck(
                        "network_none_smoke",
                        "done" if code == 0 else "partial",
                        f"exit={code}; {output or 'container ran with --network none'}",
                        "Production allowlist still needs host/firewall policy for approved RPC hosts.",
                    )
                )

    blockers = [check for check in checks if check.status == "blocked"]
    payload = {
        "kind": "wr3_sandbox_container_evidence",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "blocked" if blockers else "local_container_evidence_created",
        "production_note": "Docker evidence is not a substitute for staging VM/container egress allowlist verification.",
        "checks": [asdict(check) for check in checks],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = OUT_DIR / f"sandbox_container_evidence_{stamp}.json"
    md_path = OUT_DIR / f"sandbox_container_evidence_{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# wr3 Sandbox Container Evidence",
        "",
        f"- Created: {payload['created_at']}",
        f"- Status: {payload['status']}",
        f"- Note: {payload['production_note']}",
        "",
        "| Check | Status | Evidence | Next step |",
        "| --- | --- | --- | --- |",
    ]
    for check in checks:
        clean_evidence = check.evidence.replace("\n", " ")[:500]
        lines.append(f"| {check.id} | {check.status} | {clean_evidence} | {check.next_step} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in payload.items() if k != "checks"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
