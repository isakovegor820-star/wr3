from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "readiness"


@dataclass(frozen=True)
class Check:
    id: str
    area: str
    status: str
    evidence: str
    next_step: str
    owner: str
    blocker: bool = False


def load_dotenv() -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = ROOT / ".env"
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def env_value(values: dict[str, str], name: str) -> str:
    return os.getenv(name) or values.get(name, "")


def any_env(values: dict[str, str], names: Iterable[str]) -> bool:
    return any(bool(env_value(values, name)) for name in names)


def all_env(values: dict[str, str], names: Iterable[str]) -> bool:
    return all(bool(env_value(values, name)) for name in names)


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def free_only_mode(values: dict[str, str]) -> bool:
    return truthy(env_value(values, "WR3_FREE_ONLY_MODE")) or env_value(values, "WR3_OBJECT_STORAGE_MODE") == "local"


def tool_present(name: str) -> bool:
    if shutil.which(name) is not None:
        return True
    configured_bin_dir = os.getenv("WR3_AUDIT_TOOLS_BIN_DIR") or load_dotenv.cache.get("WR3_AUDIT_TOOLS_BIN_DIR", "")  # type: ignore[attr-defined]
    candidate_dirs = [
        configured_bin_dir,
        str(ROOT / "artifacts" / "audit-tools-venv" / "bin"),
        str(Path.home() / ".cargo" / "bin"),
    ]
    return any(bool(directory) and (Path(directory) / name).exists() for directory in candidate_dirs)


def file_exists(path: str) -> bool:
    return (ROOT / path).exists()


def dir_has_entries(path: str) -> bool:
    target = ROOT / path
    return target.exists() and any(target.iterdir())


def tcp_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run(command: list[str], timeout: int = 8) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - host dependent
        return False, str(exc)
    output = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, output[:800]


def http_json(url: str, timeout: int = 8) -> tuple[bool, int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return True, response.status, body[:500]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, exc.code, body[:500]
    except Exception as exc:  # pragma: no cover - network dependent
        return False, 0, str(exc)


def env_check(
    *,
    id: str,
    area: str,
    names: list[str],
    next_step: str,
    owner: str,
    status_when_missing: str = "blocked",
) -> Check:
    configured = any_env(load_dotenv.cache, names)  # type: ignore[attr-defined]
    evidence = "configured: " + ", ".join(names) if configured else "missing: " + " or ".join(names)
    return Check(
        id=id,
        area=area,
        status="done" if configured else status_when_missing,
        evidence=evidence,
        next_step="No action." if configured else next_step,
        owner=owner,
        blocker=status_when_missing == "blocked" and not configured,
    )


def check_group() -> list[Check]:
    values = load_dotenv.cache  # type: ignore[attr-defined]
    is_free_only = free_only_mode(values)
    backup_target = env_value(values, "WR3_BACKUP_TARGET") or ("r2" if env_value(values, "WR3_BACKUP_R2_URI") else "local")
    checks: list[Check] = []

    checks.extend(
        [
            Check(
                "production_docs",
                "production_infrastructure",
                "done" if all(file_exists(path) for path in ["docs/PRODUCTION_DEPLOYMENT.md", "infra/systemd/wr3-api.service.example", "infra/cloudflare/wrangler.toml.example"]) else "partial",
                "deployment docs/config templates present" if file_exists("docs/PRODUCTION_DEPLOYMENT.md") else "deployment docs missing",
                "Keep Oracle/Hetzner/Cloudflare commands in docs/PRODUCTION_DEPLOYMENT.md current.",
                "codex",
            ),
            Check(
                "postgres_prod_config",
                "production_infrastructure",
                "done" if file_exists("infra/postgres/postgresql.production.conf.example") and file_exists("infra/postgres/001_core_schema.sql") else "partial",
                "Postgres production config and schema present",
                "Apply schema on staging/prod Postgres and record restore drill evidence.",
                "user",
                blocker=False,
            ),
            Check(
                "redis_celery_prod_config",
                "production_infrastructure",
                "done" if file_exists("infra/redis/redis.production.conf.example") and file_exists("infra/systemd/wr3-celery.service.example") else "partial",
                "Redis and Celery systemd templates present",
                "Install Redis/Celery services on real VM.",
                "user",
            ),
            Check(
                "backup_restore_scripts",
                "production_infrastructure",
                "done" if file_exists("scripts/backup_postgres.sh") and file_exists("scripts/restore_postgres.sh") else "partial",
                "backup/restore scripts present",
                "Run a real restore drill against staging DB before public launch.",
                "user",
                blocker=True,
            ),
            env_check(
                id="cloudflare_account",
                area="production_infrastructure",
                names=["CLOUDFLARE_ACCOUNT_ID"],
                next_step="Create/use Cloudflare account, R2 bucket, D1 database, and API token.",
                owner="user",
            ),
            env_check(
                id="cloudflare_api_token",
                area="production_infrastructure",
                names=["CLOUDFLARE_API_TOKEN"],
                next_step="Create a scoped Cloudflare API token so wrangler can create/verify R2 buckets and D1.",
                owner="user",
            ),
            env_check(
                id="artifact_encryption",
                area="production_infrastructure",
                names=["WR3_ARTIFACT_ENCRYPTION_KEY"],
                next_step="Generate a production Fernet key in a secret manager, not in git.",
                owner="user",
            ),
            env_check(
                id="backup_encryption",
                area="production_infrastructure",
                names=["WR3_BACKUP_ENCRYPTION_PASSPHRASE"],
                next_step="Set backup encryption passphrase in Doppler/OCI Vault/1Password.",
                owner="user",
            ),
            env_check(
                id="backup_remote_target",
                area="production_infrastructure",
                names=["WR3_BACKUP_R2_URI"],
                next_step="Create R2 backup bucket and set WR3_BACKUP_R2_URI, or keep WR3_BACKUP_TARGET=local in free-only mode.",
                owner="user",
                status_when_missing="partial" if is_free_only else "blocked",
            ),
            Check(
                "r2_s3_credentials",
                "production_infrastructure",
                "done"
                if all_env(values, ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"])
                else ("partial" if is_free_only else "blocked"),
                "R2 S3 credentials configured"
                if all_env(values, ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"])
                else (
                    "R2 S3 credentials intentionally absent in free-only local storage mode"
                    if is_free_only
                    else "missing AWS_ACCESS_KEY_ID and/or AWS_SECRET_ACCESS_KEY for R2 S3 upload"
                ),
                "Create scoped R2 access keys later if a billing-enabled production account is available.",
                "user",
                blocker=(not is_free_only) and not all_env(values, ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]),
            ),
            Check(
                "free_local_storage_fallback",
                "production_infrastructure",
                "done" if backup_target == "local" and bool(env_value(values, "WR3_BACKUP_ENCRYPTION_PASSPHRASE")) else "partial",
                "free-only mode uses encrypted local artifacts/backups; R2 remains optional"
                if backup_target == "local"
                else f"backup target is {backup_target}",
                "Keep encrypted local restore drills until an adult/billing-enabled object store is available.",
                "codex",
            ),
            Check(
                "aws_cli",
                "production_infrastructure",
                "done" if tool_present("aws") else "partial",
                "aws CLI available" if tool_present("aws") else "aws CLI missing; required for backup upload script",
                "Install awscli before running encrypted R2 backup uploads.",
                "user",
            ),
        ]
    )

    checks.extend(
        [
            env_check(
                id="secret_manager",
                area="secrets_observability",
                names=["DOPPLER_TOKEN", "OCI_CLI_PROFILE", "OP_SERVICE_ACCOUNT_TOKEN"],
                next_step="Configure one secret manager flow; .env is local only.",
                owner="user",
            ),
            env_check(
                id="sentry",
                area="secrets_observability",
                names=["WR3_SENTRY_DSN"],
                next_step="Create Sentry project and enable sensitive scrubber before sending events.",
                owner="user",
                status_when_missing="partial",
            ),
            env_check(
                id="telegram_alert_chat",
                area="secrets_observability",
                names=["WR3_TELEGRAM_ALERT_CHAT_ID"],
                next_step="Create private ops chat and set alert chat id.",
                owner="user",
                status_when_missing="partial",
            ),
            Check(
                "sensitive_scrubber",
                "secrets_observability",
                "done" if file_exists("apps/api/wr3_api/services/observability.py") else "partial",
                "SensitiveScrubber and LLM cost ledger code present",
                "Wire Sentry SDK in production app startup after DSN exists.",
                "codex",
            ),
        ]
    )

    checks.extend(
        [
            env_check(
                id="explorer_keys",
                area="real_api_integrations",
                names=["WR3_ETHERSCAN_API_KEY", "WR3_BASESCAN_API_KEY", "WR3_BSCSCAN_API_KEY", "WR3_ARBISCAN_API_KEY"],
                next_step="Add free explorer key(s) for real verified-source scans.",
                owner="user",
                status_when_missing="partial",
            ),
            env_check(
                id="rpc_keys",
                area="real_api_integrations",
                names=["WR3_ETHEREUM_RPC_URL", "WR3_BASE_RPC_URL", "WR3_BSC_RPC_URL", "WR3_ARBITRUM_RPC_URL", "WR3_SOLANA_RPC_URL"],
                next_step="Set at least one real RPC URL per chain before fork-mode PoC.",
                owner="user",
                status_when_missing="partial",
            ),
            env_check(
                id="openrouter_zdr",
                area="real_api_integrations",
                names=["WR3_OPENROUTER_API_KEY", "OPENROUTER_API_KEY"],
                next_step="Add OpenRouter ZDR key only for private/paid LLM triage path.",
                owner="user",
                status_when_missing="partial",
            ),
            env_check(
                id="solodit",
                area="real_api_integrations",
                names=["WR3_SOLODIT_API_KEY"],
                next_step="Request Solodit API access or keep local RAG fixtures only.",
                owner="user",
                status_when_missing="partial" if file_exists("artifacts/rag/local-security-corpus.json") else "blocked",
            ),
            Check(
                "local_rag_corpus",
                "real_api_integrations",
                "done" if file_exists("artifacts/rag/local-security-corpus.json") else "partial",
                "local public-dataset RAG corpus artifact present"
                if file_exists("artifacts/rag/local-security-corpus.json")
                else "local public-dataset RAG corpus not built",
                "Run npm run benchmark:sync-external && npm run rag:build-local.",
                "codex",
            ),
            Check(
                "integration_status_api",
                "real_api_integrations",
                "done" if file_exists("apps/api/wr3_api/api/routes/integrations.py") else "partial",
                "/v1/integrations/status implementation present",
                "Use this endpoint after adding real keys to verify status without exposing secrets.",
                "codex",
            ),
        ]
    )

    tool_sets = {
        "static_tools": (["forge", "slither", "aderyn", "wake"], []),
        "poc_tools": (["forge", "anvil"], []),
        "fuzzing_tools": (["forge", "medusa"], ["ityfuzz"]),
        "solana_tools": (["trident", "solana-test-validator"], []),
    }
    for check_id, (required_names, optional_names) in tool_sets.items():
        names = [*required_names, *optional_names]
        found = [name for name in names if tool_present(name)]
        missing_required = [name for name in required_names if name not in found]
        missing_optional = [name for name in optional_names if name not in found]
        area = {
            "static_tools": "static_tools_production",
            "poc_tools": "poc_layer",
            "fuzzing_tools": "fuzzing",
            "solana_tools": "solana_beta",
        }[check_id]
        status = "done" if not missing_required else "partial"
        if check_id == "fuzzing_tools" and missing_optional and not missing_required:
            status = "done" if file_exists("infra/sandbox/tool-policy.json") else "partial"
        next_step = "Install missing required tools with docs/AUDIT_TOOLS_INSTALL.md or sandbox worker image."
        if check_id == "fuzzing_tools" and missing_optional and not missing_required:
            next_step = "ItyFuzz is optional by infra/sandbox/tool-policy.json until trusted binary or patched build exists."
        checks.append(
            Check(
                check_id,
                area,
                status,
                f"found: {', '.join(found) or 'none'}; missing_required: {', '.join(missing_required) or 'none'}; missing_optional: {', '.join(missing_optional) or 'none'}",
                next_step,
                "user",
                blocker=check_id in {"poc_tools", "fuzzing_tools"} and bool(missing_required),
            )
        )

    checks.extend(
        [
            Check(
                "sandbox_policy",
                "poc_layer",
                "done"
                if all(
                    file_exists(path)
                    for path in [
                        "infra/sandbox-policy.md",
                        "infra/sandbox/Dockerfile",
                        "infra/sandbox/entrypoint.sh",
                        "apps/api/tests/test_sandbox_policy.py",
                    ]
                )
                else "partial",
                "sandbox policy docs/tests and container template present",
                "Run egress allowlist test inside production sandbox container/VM.",
                "user",
                blocker=True,
            ),
            Check(
                "scoring_calibration_script",
                "scoring_calibration",
                "done" if file_exists("scripts/scoring_calibration.py") and file_exists("docs/SCORE_METHODOLOGY_CHANGELOG.md") else "partial",
                "calibration script and changelog present",
                "Run monthly calibration after collecting beta datasets.",
                "codex",
            ),
            Check(
                "ux_regression",
                "reports_ux_qa",
                "done" if file_exists("scripts/visual_regression.mjs") else "partial",
                "npm run qa:visual screenshot regression available"
                if file_exists("scripts/visual_regression.mjs")
                else "manual screenshots were checked for Mini App; automated visual regression not yet committed",
                "Run npm run qa:visual before beta/public UI changes.",
                "codex",
            ),
            env_check(
                id="payment_usdc",
                area="billing_payments",
                names=["WR3_USDC_RECEIVE_ADDRESS"],
                next_step="Set a USDC receive address only when accepting paid beta users.",
                owner="user",
                status_when_missing="partial",
            ),
            env_check(
                id="checkout_provider",
                area="billing_payments",
                names=["WR3_REQUEST_FINANCE_API_KEY", "WR3_POLAR_API_KEY", "WR3_LEMON_SQUEEZY_API_KEY"],
                next_step="Create one checkout/invoice provider account when needed for first paid customer.",
                owner="user",
                status_when_missing="partial",
            ),
            env_check(
                id="telegram_bot",
                area="telegram_mini_app",
                names=["WR3_TELEGRAM_BOT_TOKEN"],
                next_step="Set Telegram bot token in secret manager and run npm run telegram:publish.",
                owner="user",
                status_when_missing="partial",
            ),
            env_check(
                id="ton_connect",
                area="telegram_mini_app",
                names=["WR3_TON_CONNECT_MANIFEST_URL"],
                next_step="Add TON Connect manifest after payment UX is ready.",
                owner="user",
                status_when_missing="partial",
            ),
            Check(
                "legal_docs",
                "legal_disclosure",
                "done"
                if all(
                    file_exists(path)
                    for path in [
                        "docs/TERMS_OF_SERVICE_DRAFT.md",
                        "docs/PRIVACY_POLICY_DRAFT.md",
                        "docs/ENGAGEMENT_LETTER_DRAFT.md",
                        "docs/RESPONSIBLE_DISCLOSURE_POLICY.md",
                        "docs/REFUND_POLICY.md",
                        "docs/DATA_RETENTION_DELETION_POLICY.md",
                    ]
                )
                else "partial",
                "legal drafts present",
                "External legal reviewer must approve before paid/public launch.",
                "user",
                blocker=True,
            ),
            Check(
                "benchmark_local_fixtures",
                "benchmark_qa",
                "done"
                if all(
                    file_exists(path)
                    for path in [
                        "benchmarks/fixtures/defihacklabs_sample.json",
                        "benchmarks/fixtures/smartbugs_sample.json",
                        "benchmarks/fixtures/sealevel_attacks_sample.json",
                    ]
                )
                else "partial",
                "local benchmark fixtures present",
                "Clone/curate larger real subsets before public benchmark claims.",
                "codex",
            ),
            Check(
                "curated_benchmark_manifest",
                "benchmark_qa",
                "done" if file_exists("artifacts/benchmarks/curated-benchmark-manifest.json") else "partial",
                "curated external benchmark manifest present"
                if file_exists("artifacts/benchmarks/curated-benchmark-manifest.json")
                else "curated external benchmark manifest missing",
                "Run npm run benchmark:curate after syncing external corpora.",
                "codex",
            ),
            Check(
                "external_benchmark_corpora",
                "benchmark_qa",
                "done"
                if all(
                    dir_has_entries(path)
                    for path in [
                        "external/benchmarks/DeFiHackLabs",
                        "external/benchmarks/smartbugs-curated",
                        "external/benchmarks/sealevel-attacks",
                    ]
                )
                else "partial",
                "external corpora present under external/benchmarks"
                if all(
                    dir_has_entries(path)
                    for path in [
                        "external/benchmarks/DeFiHackLabs",
                        "external/benchmarks/smartbugs-curated",
                        "external/benchmarks/sealevel-attacks",
                    ]
                )
                else "full external corpora not present locally",
                "Run npm run benchmark:sync-external and record exact commit SHAs.",
                "codex",
                blocker=False,
            ),
            Check(
                "closed_beta_validation",
                "closed_beta_launch",
                "blocked",
                "requires real interviews, scans, and LOI/preorder evidence",
                "Complete 30 interviews, 10 live scans, 3 LOI/preorders in docs/ICP_VALIDATION_TRACKER.md.",
                "user",
                blocker=True,
            ),
            Check(
                "bug_bounty_incident_drill",
                "closed_beta_launch",
                "done"
                if file_exists("docs/BUG_BOUNTY_SETUP.md")
                and file_exists("docs/INCIDENT_RESPONSE.md")
                and any(ARTIFACT_DIR.glob("incident_tabletop_*.json"))
                else ("partial" if file_exists("docs/BUG_BOUNTY_SETUP.md") and file_exists("docs/INCIDENT_RESPONSE.md") else "blocked"),
                "bug bounty docs and local incident tabletop artifact present"
                if any(ARTIFACT_DIR.glob("incident_tabletop_*.json"))
                else "bug bounty and incident response docs present",
                "Run production team tabletop after staging is live; launch bounty only after legal and telemetry are ready.",
                "user",
                blocker=True,
            ),
        ]
    )

    if tcp_open("127.0.0.1", 8001):
        ok, status, body = http_json("http://127.0.0.1:8001/ready")
        checks.append(
            Check(
                "local_api_ready",
                "runtime_smoke",
                "done" if ok else "partial",
                f"GET /ready HTTP {status}: {body}",
                "Start npm run dev:local if local runtime is expected.",
                "codex",
            )
        )
    else:
        checks.append(
            Check(
                "local_api_ready",
                "runtime_smoke",
                "partial",
                "localhost API is not listening on 8001",
                "Start npm run dev:local when doing runtime smoke.",
                "codex",
            )
        )

    return checks


def summarize(checks: list[Check]) -> dict[str, object]:
    counts: dict[str, int] = {}
    area_counts: dict[str, dict[str, int]] = {}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
        area_counts.setdefault(check.area, {})
        area_counts[check.area][check.status] = area_counts[check.area].get(check.status, 0) + 1
    blockers = [check for check in checks if check.blocker and check.status != "done"]
    done = counts.get("done", 0)
    completion = round(done / len(checks) * 100, 1) if checks else 0.0
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "completion_percent_by_checks": completion,
        "total_checks": len(checks),
        "counts": counts,
        "areas": area_counts,
        "blocker_count": len(blockers),
    }


def write_artifacts(summary: dict[str, object], checks: list[Check]) -> tuple[Path, Path]:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = ARTIFACT_DIR / f"production_readiness_{stamp}.json"
    md_path = ARTIFACT_DIR / f"production_readiness_{stamp}.md"
    payload = {"summary": summary, "checks": [asdict(check) for check in checks]}
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# wr3 Production Readiness",
        "",
        f"Generated: `{summary['generated_at']}`",
        f"Completion by checks: **{summary['completion_percent_by_checks']}%**",
        f"Checks: **{summary['total_checks']}**",
        f"Blockers: **{summary['blocker_count']}**",
        "",
        "| Area | ID | Status | Owner | Evidence | Next step |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for check in checks:
        lines.append(
            f"| {check.area} | {check.id} | {check.status} | {check.owner} | "
            f"{check.evidence.replace('|', '/')} | {check.next_step.replace('|', '/')} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check wr3 production/public launch readiness without printing secrets.")
    parser.add_argument("--json", action="store_true", help="Print JSON payload instead of human summary.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when launch blockers remain.")
    args = parser.parse_args()

    load_dotenv.cache = load_dotenv()  # type: ignore[attr-defined]
    checks = check_group()
    summary = summarize(checks)
    json_path, md_path = write_artifacts(summary, checks)

    if args.json:
        print(json.dumps({"summary": summary, "checks": [asdict(check) for check in checks]}, indent=2, ensure_ascii=False))
    else:
        print("wr3 production readiness")
        print(f"completion_by_checks={summary['completion_percent_by_checks']}%")
        print(f"counts={summary['counts']}")
        print(f"blockers={summary['blocker_count']}")
        print(f"json_artifact={json_path.relative_to(ROOT)}")
        print(f"markdown_artifact={md_path.relative_to(ROOT)}")
        blockers = [check for check in checks if check.blocker and check.status != "done"]
        if blockers:
            print("blocking_next_steps:")
            for check in blockers[:12]:
                print(f"- [{check.area}] {check.id}: {check.next_step}")

    return 1 if args.strict and int(summary["blocker_count"]) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
