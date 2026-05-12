from __future__ import annotations

import argparse
import csv
import json
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def npm_dependencies() -> list[dict[str, str]]:
    lock_path = ROOT / "package-lock.json"
    if not lock_path.exists():
        return []
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    packages = lock.get("packages", {})
    rows: list[dict[str, str]] = []
    if not isinstance(packages, dict):
        return rows
    for path, payload in sorted(packages.items()):
        if not path.startswith("node_modules/") or not isinstance(payload, dict):
            continue
        name = path.removeprefix("node_modules/")
        rows.append(
            {
                "ecosystem": "npm",
                "name": str(payload.get("name") or name),
                "version": str(payload.get("version") or ""),
                "license": license_for_node_package(path, payload),
                "path": path,
            }
        )
    return rows


def license_for_node_package(path: str, payload: dict[str, Any]) -> str:
    declared = payload.get("license")
    if isinstance(declared, str):
        return declared
    package_json = ROOT / path / "package.json"
    if package_json.exists():
        try:
            package_payload = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "unknown"
        package_license = package_payload.get("license")
        if isinstance(package_license, str):
            return package_license
    return "unknown"


def python_dependencies() -> list[dict[str, str]]:
    pyproject_path = ROOT / "apps" / "api" / "pyproject.toml"
    if not pyproject_path.exists():
        return []
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8")).get("project", {})
    rows: list[dict[str, str]] = []
    for dependency in project.get("dependencies", []):
        name = str(dependency).split(">", 1)[0].split("<", 1)[0].split("=", 1)[0].strip()
        rows.append(
            {
                "ecosystem": "python",
                "name": name,
                "version": str(dependency),
                "license": "lookup_required",
                "path": "apps/api/pyproject.toml",
            }
        )
    for extra, dependencies in project.get("optional-dependencies", {}).items():
        for dependency in dependencies:
            name = str(dependency).split(">", 1)[0].split("<", 1)[0].split("=", 1)[0].strip()
            rows.append(
                {
                    "ecosystem": f"python[{extra}]",
                    "name": name,
                    "version": str(dependency),
                    "license": "lookup_required",
                    "path": "apps/api/pyproject.toml",
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate wr3 dependency license inventory CSV.")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts" / "licenses.csv")
    args = parser.parse_args()

    rows = npm_dependencies() + python_dependencies()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ecosystem", "name", "version", "license", "path"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
