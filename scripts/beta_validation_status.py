from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "docs" / "ICP_VALIDATION_TRACKER.md"
OUT_DIR = ROOT / "artifacts" / "readiness"

TARGETS = {
    "Interviews": 30,
    "Live scans": 10,
    "LOI/preorders": 3,
}


def parse_current_counts() -> dict[str, int]:
    if not TRACKER.exists():
        return {key: 0 for key in TARGETS}
    text = TRACKER.read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    for label in TARGETS:
        pattern = re.compile(rf"\|\s*{re.escape(label)}\s*\|\s*\d+\s*\|\s*(\d+)\s*\|", re.IGNORECASE)
        match = pattern.search(text)
        counts[label] = int(match.group(1)) if match else 0
    return counts


def main() -> int:
    current = parse_current_counts()
    items = []
    for label, target in TARGETS.items():
        value = current.get(label, 0)
        items.append(
            {
                "signal": label,
                "target": target,
                "current": value,
                "remaining": max(target - value, 0),
                "status": "done" if value >= target else "blocked",
            }
        )
    blockers = [item for item in items if item["status"] != "done"]
    payload = {
        "kind": "wr3_beta_validation_status",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "done" if not blockers else "blocked",
        "tracker": str(TRACKER.relative_to(ROOT)),
        "items": items,
        "note": "This evidence cannot be faked by code; real interviews, live scans, and LOI/preorders must be recorded by the founder/product owner.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = OUT_DIR / f"beta_validation_status_{stamp}.json"
    md_path = OUT_DIR / f"beta_validation_status_{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# wr3 Beta Validation Status",
        "",
        f"- Created: {payload['created_at']}",
        f"- Status: {payload['status']}",
        f"- Tracker: `{payload['tracker']}`",
        "",
        "| Signal | Target | Current | Remaining | Status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for item in items:
        lines.append(
            f"| {item['signal']} | {item['target']} | {item['current']} | {item['remaining']} | {item['status']} |"
        )
    lines.extend(["", payload["note"]])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in payload.items() if k != "items"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
