from __future__ import annotations

import json
import os
import shutil
import socket
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "artifacts" / "readiness"


@dataclass(frozen=True)
class PreflightCheck:
    id: str
    status: str
    evidence: str
    next_step: str
    external: bool = False


def file_exists(path: str) -> bool:
    return (ROOT / path).exists()


def tcp_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    staging_host = os.getenv("WR3_STAGING_HOST", "").strip()
    checks = [
        PreflightCheck(
            "postgres_schema",
            "done" if file_exists("infra/postgres/001_core_schema.sql") else "partial",
            "infra/postgres/001_core_schema.sql present" if file_exists("infra/postgres/001_core_schema.sql") else "core schema missing",
            "Apply schema on staging Postgres 17.",
        ),
        PreflightCheck(
            "pgvector_schema",
            "done" if file_exists("infra/postgres/002_pgvector_knowledge_schema.sql") else "partial",
            "pgvector schema present" if file_exists("infra/postgres/002_pgvector_knowledge_schema.sql") else "pgvector schema missing",
            "Apply only when RAG/vector search is enabled.",
        ),
        PreflightCheck(
            "redis_config",
            "done" if file_exists("infra/redis/redis.production.conf.example") else "partial",
            "Redis production config template present",
            "Install Redis on staging VM and enable persistence policy.",
        ),
        PreflightCheck(
            "celery_systemd",
            "done"
            if file_exists("infra/systemd/wr3-celery.service.example")
            and file_exists("infra/systemd/wr3-celery-beat.service.example")
            else "partial",
            "Celery worker/beat systemd templates present",
            "Install worker services on staging VM.",
        ),
        PreflightCheck(
            "backup_restore_scripts",
            "done" if file_exists("scripts/backup_postgres.sh") and file_exists("scripts/restore_postgres.sh") else "partial",
            "backup/restore scripts present",
            "Run restore drill against staging DB.",
        ),
        PreflightCheck(
            "local_postgres",
            "done" if tcp_open("127.0.0.1", 5432) else "skipped",
            "127.0.0.1:5432 open" if tcp_open("127.0.0.1", 5432) else "local Postgres not reachable in this shell",
            "Local-only evidence; staging requires WR3_STAGING_HOST.",
        ),
        PreflightCheck(
            "local_redis",
            "done" if tcp_open("127.0.0.1", 6379) else "skipped",
            "127.0.0.1:6379 open" if tcp_open("127.0.0.1", 6379) else "local Redis not reachable in this shell",
            "Local-only evidence; staging requires WR3_STAGING_HOST.",
        ),
        PreflightCheck(
            "staging_host",
            "ready_to_check" if staging_host else "blocked",
            "WR3_STAGING_HOST configured" if staging_host else "WR3_STAGING_HOST missing",
            "Set WR3_STAGING_HOST after a real Oracle/Hetzner VM exists.",
            external=True,
        ),
        PreflightCheck(
            "ssh_client",
            "done" if shutil.which("ssh") else "partial",
            "ssh client available" if shutil.which("ssh") else "ssh client missing",
            "Use SSH for staging deploy/restore drill.",
        ),
    ]
    blockers = [check for check in checks if check.external and check.status == "blocked"]
    payload = {
        "kind": "wr3_staging_preflight",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "blocked" if blockers else "ready_for_manual_staging_check",
        "blockers": [check.id for check in blockers],
        "checks": [asdict(check) for check in checks],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = OUT_DIR / f"staging_preflight_{stamp}.json"
    md_path = OUT_DIR / f"staging_preflight_{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# wr3 Staging Preflight",
        "",
        f"- Created: {payload['created_at']}",
        f"- Status: {payload['status']}",
        "",
        "| Check | Status | Evidence | Next step |",
        "| --- | --- | --- | --- |",
    ]
    for check in checks:
        lines.append(f"| {check.id} | {check.status} | {check.evidence} | {check.next_step} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in payload.items() if k != "checks"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
