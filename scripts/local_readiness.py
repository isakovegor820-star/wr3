from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
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
REQUIRED_TOOL_IDS = {"foundry_forge", "slither", "aderyn", "wake"}
WEB_ROUTES = [
    ("/", "home"),
    ("/tools", "tools_status_page"),
    ("/integrations", "integrations_status_page"),
    ("/dashboard", "dashboard"),
    ("/telegram-emulator", "telegram_emulator"),
    ("/tg", "telegram_mini_app_preview"),
    ("/disclosure", "disclosure_ui"),
]
FIXTURE_FILES = [
    "benchmarks/fixtures/defihacklabs_sample.json",
    "benchmarks/fixtures/smartbugs_sample.json",
    "benchmarks/fixtures/sealevel_attacks_sample.json",
    "benchmarks/fixtures/poc_cases.json",
    "benchmarks/fixtures/fuzzing_cases.json",
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


def http_request(url: str, *, method: str = "GET", payload: dict[str, object] | None = None, timeout: int = 8):
    body = None
    headers = {"content-type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            try:
                return True, response.status, json.loads(raw)
            except json.JSONDecodeError:
                return True, response.status, raw[:500]
    except urllib.error.HTTPError as exc:
        return False, exc.code, exc.read().decode("utf-8", errors="replace")[:500]
    except Exception as exc:  # pragma: no cover - local machine dependent
        return False, 0, str(exc)


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


def api_checks(api_running: bool) -> list[Check]:
    if not api_running:
        return [
            Check(
                "tools_status_api",
                "api",
                "manual",
                "API is not running, skipped /v1/tools/status",
                "Start localhost stack with npm run dev:local.",
            ),
            Check(
                "integrations_status_api",
                "api",
                "manual",
                "API is not running, skipped /v1/integrations/status",
                "Start localhost stack with npm run dev:local.",
            ),
            Check(
                "basic_scan_flow",
                "api",
                "manual",
                "API is not running, skipped local scan flow",
                "Start localhost stack with npm run dev:local.",
            ),
        ]

    ok, status, payload = http_request("http://127.0.0.1:8001/v1/tools/status")
    checks = [
        Check(
            "tools_status_api",
            "api",
            "configured" if ok else "todo",
            f"HTTP {status}; {payload.get('status') if isinstance(payload, dict) else payload}",
            "Fix /v1/tools/status route before local UX QA.",
        )
    ]
    integrations_ok, integrations_status, integrations_payload = http_request("http://127.0.0.1:8001/v1/integrations/status")
    checks.append(
        Check(
            "integrations_status_api",
            "api",
            "configured" if integrations_ok else "todo",
            f"HTTP {integrations_status}; {integrations_payload.get('status') if isinstance(integrations_payload, dict) else integrations_payload}",
            "Fix /v1/integrations/status route before API integration QA.",
        )
    )
    if ok and isinstance(payload, dict):
        installed = {
            item.get("id")
            for item in payload.get("tools", [])
            if isinstance(item, dict) and item.get("installed") is True
        }
        missing = sorted(REQUIRED_TOOL_IDS - installed)
        checks.append(
            Check(
                "required_audit_tools",
                "tools",
                "configured" if not missing else "optional",
                "all required local audit tools installed" if not missing else f"missing optional local tools: {', '.join(missing)}",
                "Use docs/AUDIT_TOOLS_INSTALL.md when you want real Foundry/Slither/Aderyn/Wake runs.",
            )
        )

    scan_payload = {
        "chain": "base",
        "address": "0x0000000000000000000000000000000000000100",
        "source": "contract Readiness { function auth(address a) public { require(tx.origin == a); } }",
        "requested_depth": "preliminary",
        "visibility": "private",
        "user_intent": "pre_launch_self_check",
    }
    scan_ok, scan_status, scan_result = http_request(
        "http://127.0.0.1:8001/v1/audits",
        method="POST",
        payload=scan_payload,
    )
    checks.append(
        Check(
            "basic_scan_flow",
            "api",
            "configured" if scan_ok and scan_status == 200 else "todo",
            f"HTTP {scan_status}; audit_id={scan_result.get('audit_id') if isinstance(scan_result, dict) else scan_result}",
            "Fix POST /v1/audits local scan flow.",
        )
    )
    return checks


def web_route_checks(web_running: bool) -> list[Check]:
    if not web_running:
        return [
            Check(
                "web_routes",
                "web",
                "manual",
                "Web is not running, skipped route checks",
                "Start localhost stack with npm run dev:local.",
            )
        ]
    checks: list[Check] = []
    for path, label in WEB_ROUTES:
        ok, status, _payload = http_request(f"http://127.0.0.1:3001{path}", timeout=10)
        checks.append(
            Check(
                label,
                "web",
                "configured" if ok and status == 200 else "todo",
                f"{path} HTTP {status}",
                f"Fix web route {path}.",
            )
        )
    return checks


def fixture_checks() -> list[Check]:
    checks = []
    for fixture in FIXTURE_FILES:
        path = ROOT / fixture
        checks.append(
            Check(
                f"fixture:{Path(fixture).stem}",
                "benchmark",
                "configured" if path.exists() else "todo",
                f"{fixture} exists" if path.exists() else f"{fixture} missing",
                "Create local fixture or document external dataset import.",
            )
        )
    return checks


def main() -> int:
    values = env_file_values()
    artifact_dir = values.get("WR3_ARTIFACT_DIR") or "artifacts/local"
    api_running = tcp_open("127.0.0.1", 8001)
    web_running = tcp_open("127.0.0.1", 3001)
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
            "configured" if api_running else "manual",
            "API port 8001 is open" if api_running else "API is not currently running",
            "Start localhost stack with npm run dev:local.",
        ),
        Check(
            "web_port",
            "runtime",
            "configured" if web_running else "manual",
            "Web port 3001 is open" if web_running else "Web is not currently running",
            "Start localhost stack with npm run dev:local.",
        ),
        Check(
            "artifact_dir",
            "storage",
            "configured" if (ROOT / artifact_dir).exists() else "todo",
            f"{artifact_dir} exists" if (ROOT / artifact_dir).exists() else f"{artifact_dir} missing",
            "Create artifact dir by running a scan or mkdir -p artifacts/local.",
        ),
        Check(
            "artifact_encryption_key",
            "storage",
            "configured" if values.get("WR3_ARTIFACT_ENCRYPTION_KEY") or os.getenv("WR3_ARTIFACT_ENCRYPTION_KEY") else "todo",
            "artifact encryption key configured" if values.get("WR3_ARTIFACT_ENCRYPTION_KEY") or os.getenv("WR3_ARTIFACT_ENCRYPTION_KEY") else "artifact encryption key missing",
            "Run scripts/setup_native_localhost.sh or set WR3_ARTIFACT_ENCRYPTION_KEY for private artifacts.",
        ),
    ]
    checks.extend(postgres_checks(values))
    checks.extend(fixture_checks())
    checks.extend(api_checks(api_running))
    checks.extend(web_route_checks(web_running))

    local_commands = [
        ("poc_local_command", "poc", ["npm", "run", "poc:local"]),
        ("fuzzing_local_command", "fuzzing", ["npm", "run", "fuzzing:local"]),
    ]
    for check_id, area, command in local_commands:
        ok, output = run(command, timeout=45)
        checks.append(
            Check(
                check_id,
                area,
                "configured" if ok else "todo",
                f"{' '.join(command)} completed"
                if ok
                else (output.splitlines()[-1] if output else "command failed without output"),
                f"Fix {' '.join(command)}.",
            )
        )
    run_long_benchmarks = (
        values.get("WR3_READINESS_RUN_LONG_BENCHMARKS") == "true"
        or os.getenv("WR3_READINESS_RUN_LONG_BENCHMARKS") == "true"
    )
    if run_long_benchmarks:
        benchmark_timeout = int(
            values.get("WR3_READINESS_BENCHMARK_TIMEOUT_SECONDS")
            or os.getenv("WR3_READINESS_BENCHMARK_TIMEOUT_SECONDS")
            or 180
        )
        ok, output = run(["npm", "run", "benchmark:local"], timeout=benchmark_timeout)
        checks.append(
            Check(
                "benchmark_local_command",
                "benchmark",
                "configured" if ok else "todo",
                "npm run benchmark:local completed"
                if ok
                else (output.splitlines()[-1] if output else "command failed without output"),
                "Increase WR3_READINESS_BENCHMARK_TIMEOUT_SECONDS or inspect npm run benchmark:local.",
            )
        )
    else:
        checks.append(
            Check(
                "benchmark_local_command",
                "benchmark",
                "manual",
                "Long benchmark skipped by local:readiness default path",
                "Run WR3_READINESS_RUN_LONG_BENCHMARKS=true npm run local:readiness or npm run benchmark:local.",
            )
        )

    summary = {
        "configured": sum(check.status == "configured" for check in checks),
        "partial": sum(check.status == "partial" for check in checks),
        "todo": sum(check.status == "todo" for check in checks),
        "manual": sum(check.status == "manual" for check in checks),
        "optional": sum(check.status == "optional" for check in checks),
    }
    readiness = {
        "passed": summary["configured"],
        "failed": summary["todo"] + summary["partial"],
        "skipped": summary["optional"] + summary["manual"],
    }
    print(json.dumps({"readiness": readiness, "summary": summary, "checks": [asdict(check) for check in checks]}, indent=2))
    return 0 if summary["todo"] == 0 and summary["partial"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
