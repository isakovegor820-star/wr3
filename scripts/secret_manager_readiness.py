from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "artifacts" / "readiness"


@dataclass(frozen=True)
class SecretManagerOption:
    id: str
    cli: str
    installed: bool
    auth_signal: bool
    status: str
    evidence: str
    next_step: str


def env_present(*names: str) -> bool:
    return any(bool(os.getenv(name, "").strip()) for name in names)


def option_status(
    *,
    id: str,
    cli: str,
    auth_signal: bool,
    auth_description: str,
    next_step: str,
) -> SecretManagerOption:
    installed = shutil.which(cli) is not None
    if installed and auth_signal:
        status = "ready_for_staging_secrets"
    elif installed:
        status = "cli_installed_auth_missing"
    else:
        status = "missing"
    evidence = f"{cli} cli={'installed' if installed else 'missing'}; {auth_description}={'present' if auth_signal else 'missing'}"
    return SecretManagerOption(id, cli, installed, auth_signal, status, evidence, next_step)


def main() -> int:
    options = [
        option_status(
            id="doppler",
            cli="doppler",
            auth_signal=env_present("DOPPLER_TOKEN"),
            auth_description="DOPPLER_TOKEN",
            next_step="Install Doppler CLI and set a project-scoped service token outside git.",
        ),
        option_status(
            id="onepassword",
            cli="op",
            auth_signal=env_present("OP_SERVICE_ACCOUNT_TOKEN"),
            auth_description="OP_SERVICE_ACCOUNT_TOKEN",
            next_step="Install 1Password CLI and set a service-account token outside git.",
        ),
        option_status(
            id="oci_vault",
            cli="oci",
            auth_signal=env_present("OCI_CLI_PROFILE", "OCI_CONFIG_FILE"),
            auth_description="OCI_CLI_PROFILE or OCI_CONFIG_FILE",
            next_step="Install OCI CLI and configure a profile with Vault read access.",
        ),
    ]
    ready = [option for option in options if option.status == "ready_for_staging_secrets"]
    payload = {
        "kind": "wr3_secret_manager_readiness",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "ready" if ready else "blocked",
        "ready_options": [option.id for option in ready],
        "safety": [
            "No secret values are printed or stored in this artifact.",
            ".env is allowed for localhost only, not staging/prod.",
            "Sandbox workers must not receive secret-manager tokens.",
        ],
        "options": [asdict(option) for option in options],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = OUT_DIR / f"secret_manager_readiness_{stamp}.json"
    md_path = OUT_DIR / f"secret_manager_readiness_{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# wr3 Secret Manager Readiness",
        "",
        f"- Created: {payload['created_at']}",
        f"- Status: {payload['status']}",
        "- Safety: no secret values are printed.",
        "",
        "| Option | Status | Evidence | Next step |",
        "| --- | --- | --- | --- |",
    ]
    for option in options:
        lines.append(f"| {option.id} | {option.status} | {option.evidence} | {option.next_step} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in payload.items() if k != "options"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
