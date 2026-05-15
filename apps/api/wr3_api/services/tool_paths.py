from __future__ import annotations

import os
import shutil
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
