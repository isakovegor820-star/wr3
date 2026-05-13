from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_TABLES = [
    "audit_jobs",
    "audit_events",
    "engine_runs",
    "findings",
    "artifacts",
    "disclosure_cases",
]


@dataclass(frozen=True)
class Check:
    id: str
    area: str
    status: str
    evidence: str
    next_step: str


def env_file_values() -> dict[str, str]:
    env_path = ROOT / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip("'").strip('"')
    return values


def tool(name: str) -> str | None:
    return shutil.which(name)


def run(command: list[str], timeout: int = 5) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - depends on local machine state
        return False, str(exc)
    output = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, output


def tcp_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def postgres_checks(values: dict[str, str]) -> list[Check]:
    psql = tool("psql")
    if psql is None:
        return [
            Check(
                "postgres_cli",
                "database",
                "todo",
                "psql not found in PATH",
                "Run scripts/setup_native_localhost.sh or install postgresql@17 with Homebrew.",
            )
        ]

    db_url = values.get("WR3_DATABASE_URL") or os.getenv("WR3_DATABASE_URL") or "postgresql:///wr3_local"
    ok, output = run([psql, db_url, "-Atqc", "select current_database()"])
    checks = [
        Check(
            "postgres_connection",
            "database",
            "configured" if ok else "todo",
            output if ok else output or f"Could not connect with {db_url}",
            "Run scripts/setup_native_localhost.sh and verify brew services list.",
        )
    ]
    if not ok:
        return checks

    table_sql = "select tablename from pg_tables where schemaname = 'public' order by tablename"
    tables_ok, tables_output = run([psql, db_url, "-Atqc", table_sql])
    found_tables = set(tables_output.splitlines()) if tables_ok else set()
    missing = [table for table in CORE_TABLES if table not in found_tables]
    checks.append(
        Check(
            "postgres_schema",
            "database",
            "configured" if not missing else "partial",
            "core tables present" if not missing else f"missing tables: {', '.join(missing)}",
            "Apply infra/postgres/001_core_schema.sql.",
        )
    )

    vector_ok, vector_output = run(
        [psql, db_url, "-Atqc", "select 1 from pg_extension where extname = 'vector'"]
    )
    checks.append(
        Check(
            "pgvector",
            "database",
            "configured" if vector_ok and vector_output == "1" else "optional",
            "pgvector extension enabled" if vector_ok and vector_output == "1" else "pgvector not enabled; RAG vector schema can be skipped locally",
            "Install pgvector and run infra/postgres/002_pgvector_knowledge_schema.sql when RAG moves beyond fixtures.",
        )
    )
    return checks


def main() -> int:
    values = env_file_values()
    artifact_dir = values.get("WR3_ARTIFACT_DIR") or "artifacts/local"
    checks: list[Check] = [
        Check(
            "env_file",
            "config",
            "configured" if (ROOT / ".env").exists() else "todo",
            ".env present" if (ROOT / ".env").exists() else ".env missing",
            "Run scripts/setup_native_localhost.sh to generate local .env.",
        ),
        Check(
            "node_dependencies",
            "runtime",
            "configured" if (ROOT / "node_modules").exists() else "todo",
            "node_modules present" if (ROOT / "node_modules").exists() else "node_modules missing",
            "Run npm install.",
        ),
        Check(
            "api_venv",
            "runtime",
            "configured" if (ROOT / "apps/api/.venv/bin/python").exists() else "todo",
            "apps/api/.venv present" if (ROOT / "apps/api/.venv/bin/python").exists() else "API venv missing",
            'Run python3 -m venv apps/api/.venv && apps/api/.venv/bin/python -m pip install -e "apps/api[dev,worker,secure]".',
        ),
        Check(
            "redis",
            "queue",
            "configured" if tool("redis-cli") and run(["redis-cli", "ping"])[0] else "todo",
            "Redis PING ok" if tool("redis-cli") and run(["redis-cli", "ping"])[0] else "Redis is not responding locally",
            "Run scripts/setup_native_localhost.sh or brew services start redis.",
        ),
        Check(
            "api_port",
            "runtime",
            "configured" if tcp_open("127.0.0.1", 8001) else "manual",
            "API port 8001 is open" if tcp_open("127.0.0.1", 8001) else "API is not currently running",
            "Start API with npm run dev:api.",
        ),
        Check(
            "web_port",
            "runtime",
            "configured" if tcp_open("127.0.0.1", 3001) else "manual",
            "Web port 3001 is open" if tcp_open("127.0.0.1", 3001) else "Web is not currently running",
            "Start web with npm run dev:web.",
        ),
        Check(
            "artifact_dir",
            "storage",
            "configured" if (ROOT / artifact_dir).exists() else "todo",
            f"{artifact_dir} exists" if (ROOT / artifact_dir).exists() else f"{artifact_dir} missing",
            "Create artifact dir by running a scan or mkdir -p artifacts/local.",
        ),
    ]
    checks.extend(postgres_checks(values))

    summary = {
        "configured": sum(check.status == "configured" for check in checks),
        "partial": sum(check.status == "partial" for check in checks),
        "todo": sum(check.status == "todo" for check in checks),
        "manual": sum(check.status == "manual" for check in checks),
        "optional": sum(check.status == "optional" for check in checks),
    }
    print(json.dumps({"summary": summary, "checks": [asdict(check) for check in checks]}, indent=2))
    return 0 if summary["todo"] == 0 and summary["partial"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
