from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_AUDIT_TOOLS_BIN_DIR = ROOT / "artifacts" / "audit-tools-venv" / "bin"
DEFAULT_CARGO_BIN_DIR = Path.home() / ".cargo" / "bin"


def audit_tool_bin_dirs() -> list[Path]:
    dirs: list[Path] = []
    configured = os.getenv("WR3_AUDIT_TOOLS_BIN_DIR")
    if configured:
        dirs.append(Path(configured).expanduser())
    dirs.append(DEFAULT_AUDIT_TOOLS_BIN_DIR)
    dirs.append(DEFAULT_CARGO_BIN_DIR)
    return dirs


def resolve_tool_binary(binary: str) -> str | None:
    path = shutil.which(binary)
    if path:
        return path
    for directory in audit_tool_bin_dirs():
        candidate = directory / binary
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


_SENSITIVE_ENV_MARKERS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "CREDENTIAL",
    "_URL",
    "DSN",
)


def _is_sensitive_env_name(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in _SENSITIVE_ENV_MARKERS)


def tool_subprocess_env() -> dict[str, str]:
    """Environment for engine subprocesses (slither/wake/aderyn/foundry/medusa).

    Two jobs:

    1. Prepend the API venv bin (where ``solc-select`` installs the ``solc`` shim)
       and the audit-tool bin dirs to PATH, so the compiler and analyzers are found
       regardless of how the API process itself was launched. Without this, Slither
       silently fails to compile (no ``solc`` on PATH) and falls back to skipped.
    2. Strip secrets from the environment. These tools compile and run analysis on
       UNTRUSTED contract source, so a crash/RCE in ``solc`` or an analyzer on a
       hostile contract must not be able to read API keys, DB/broker URLs or the
       artifact encryption key. We pass only non-sensitive variables.
    """
    extra = [str(Path(sys.executable).resolve().parent)]
    extra += [str(directory) for directory in audit_tool_bin_dirs()]
    env = {
        name: value
        for name, value in os.environ.items()
        if not _is_sensitive_env_name(name)
    }
    existing = env.get("PATH", "").split(os.pathsep) if env.get("PATH") else []
    prepend = [path for path in extra if path and path not in existing]
    if prepend:
        env["PATH"] = os.pathsep.join([*prepend, *existing])
    return env
