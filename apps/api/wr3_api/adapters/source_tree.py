from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


FILE_MARKER_RE = re.compile(r"^// file: (?P<path>.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class MaterializedSourceTree:
    root: Path
    targets: list[Path]
    multi_file: bool


def materialize_source_tree(root: Path, source: str, *, default_file_name: str = "Contract.sol") -> MaterializedSourceTree:
    """Write explorer or pasted source into a Solidity project-like tree.

    Etherscan V2 standard-json sources are normalized earlier into blocks that
    start with `// file: <path>`. Static tools need those blocks as real files;
    feeding them as one Contract.sol creates fake SPDX/import errors.
    """

    blocks = _split_marked_files(source)
    if not blocks:
        target = root / _safe_path(default_file_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        return MaterializedSourceTree(root=root, targets=[target], multi_file=False)

    targets: list[Path] = []
    for file_name, content in blocks:
        target = root / _safe_path(file_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.strip() + "\n", encoding="utf-8")
        targets.append(target)
    return MaterializedSourceTree(root=root, targets=targets, multi_file=True)


def _split_marked_files(source: str) -> list[tuple[str, str]]:
    matches = list(FILE_MARKER_RE.finditer(source))
    if not matches:
        return []
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        blocks.append((match.group("path").strip(), source[start:end]))
    return blocks


def _safe_path(file_name: str) -> Path:
    normalized = Path(file_name.strip().replace("\\", "/"))
    safe_parts = [
        part
        for part in normalized.parts
        if part not in {"", ".", ".."} and not part.startswith("/")
    ]
    if not safe_parts:
        return Path("Contract.sol")
    return Path(*safe_parts)
