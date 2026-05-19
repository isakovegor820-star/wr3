#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def run_once(
    api_base: str,
    *,
    limit: int,
    min_tvl_usd: float,
    chains: list[str],
    all_networks: bool,
    requested_depth: str,
    tier: str,
) -> int:
    endpoint = "run-all" if all_networks else "run-once"
    url = f"{api_base.rstrip('/')}/v1/monitoring/scout/{endpoint}"
    payload: dict[str, object] = {
        "min_tvl_usd": min_tvl_usd,
        "chains": chains,
        "dry_run": False,
        "requested_depth": requested_depth,
        "tier": tier,
    }
    if all_networks:
        payload["per_chain_limit"] = limit
    else:
        payload["limit"] = limit
    result = post_json(url, payload)
    timestamp = datetime.now(timezone.utc).isoformat()
    print(
        f"[{timestamp}] scout-run source={result.get('source')} "
        f"discovered={result.get('discovered_count')} queued={result.get('queued_count')} "
        f"skipped={result.get('skipped_count')}"
    )
    for audit in result.get("audits", []):
        if not isinstance(audit, dict):
            continue
        print(
            "  audit "
            f"{audit.get('protocol_name')} {audit.get('chain')}:{audit.get('address')} "
            f"/audits/{audit.get('audit_id')}?owner_token={audit.get('owner_access_token')}"
        )
    return int(result.get("queued_count") or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run wr3 local 24/7 scout loop.")
    parser.add_argument("--once", action="store_true", help="Run one scout pass and exit.")
    parser.add_argument("--api-base", default=os.getenv("WR3_SCOUT_API_BASE", "http://127.0.0.1:8001"))
    parser.add_argument("--interval", type=int, default=int(os.getenv("WR3_SCOUT_INTERVAL_SECONDS", "900")))
    parser.add_argument("--limit", type=int, default=int(os.getenv("WR3_SCOUT_LIMIT", "5")))
    parser.add_argument("--min-tvl-usd", type=float, default=float(os.getenv("WR3_SCOUT_MIN_TVL_USD", "1000000")))
    parser.add_argument(
        "--chains",
        default=os.getenv("WR3_SCOUT_CHAINS", "base,ethereum,bsc,arbitrum,solana"),
        help="Comma-separated supported chains, or empty for all.",
    )
    parser.add_argument("--single-source", action="store_true", help="Use run-once instead of all-network cycle.")
    parser.add_argument("--depth", default=os.getenv("WR3_SCOUT_DEPTH", "deep"), choices=["preliminary", "standard", "deep"])
    parser.add_argument("--tier", default=os.getenv("WR3_SCOUT_TIER", "team"), choices=["free", "hobby", "team", "pro"])
    args = parser.parse_args()
    chains = [item.strip() for item in args.chains.split(",") if item.strip()]

    while True:
        try:
            run_once(
                args.api_base,
                limit=args.limit,
                min_tvl_usd=args.min_tvl_usd,
                chains=chains,
                all_networks=not args.single_source,
                requested_depth=args.depth,
                tier=args.tier,
            )
        except urllib.error.URLError as exc:
            print(f"[scout-loop] API unavailable: {exc}")
        except Exception as exc:
            print(f"[scout-loop] run failed: {exc.__class__.__name__}: {exc}")
        if args.once:
            return 0
        time.sleep(max(args.interval, 60))


if __name__ == "__main__":
    raise SystemExit(main())
