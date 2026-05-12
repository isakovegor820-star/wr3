from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from wr3_api.services.audit_service import AuditService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run wr3 tier-based retention sweep.")
    parser.add_argument("--dry-run", action="store_true", help="report expired audits without deleting")
    args = parser.parse_args()

    result = AuditService().run_retention_sweep(dry_run=args.dry_run)
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
