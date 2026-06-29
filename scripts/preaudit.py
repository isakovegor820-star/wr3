#!/usr/bin/env python3
"""wr3 pre-audit — point at a Solidity file, get a clean, sellable report.

    python scripts/preaudit.py path/to/Contract.sol [--deep] [--chain ethereum]

Writes <name>-report.html (open in a browser → print to PDF → hand to the client)
and <name>-report.md next to the source. Runs fully locally and PRIVATELY: an
in-memory repo, no production DB, no LLM spend by default.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "apps" / "api"))

# Isolated + private + free: in-memory repo (never touches the prod DB / client
# contracts stay off disk-at-rest), deterministic triage (no navy spend), dev mode
# (so the fail-closed encryption check stays lenient with no key).
os.environ["WR3_DATABASE_URL"] = ""
os.environ["WR3_ARTIFACT_ENCRYPTION_KEY"] = ""
os.environ.setdefault("WR3_LLM_PROVIDER", "disabled")
os.environ["WR3_ENVIRONMENT"] = "development"
os.environ["PATH"] = (
    "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:"
    + os.environ.get("PATH", "")
    + ":" + str(Path.home() / ".cargo" / "bin")
)

from wr3_api.core.config import get_settings  # noqa: E402

get_settings.cache_clear()
from wr3_api.domain.enums import Chain  # noqa: E402
from wr3_api.domain.schemas import CreateAuditRequest  # noqa: E402
from wr3_api.services.audit_service import AuditService  # noqa: E402
from wr3_api.services.report_renderer import ReportRenderer  # noqa: E402


async def run(path: Path, depth: str, chain: str) -> int:
    source = path.read_text(encoding="utf-8")
    print(f"⏳ Анализирую {path.name} (глубина: {depth})… это займёт ~минуту")
    svc = AuditService()
    record = await svc.create_audit(
        CreateAuditRequest(chain=Chain(chain), source=source, requested_depth=depth)
    )
    await svc.process_audit(record.audit_id)
    record = svc.get_record(record.audit_id)

    renderer = ReportRenderer()
    stem = path.with_suffix("")
    html_path = Path(f"{stem}-report.html")
    md_path = Path(f"{stem}-report.md")
    html_path.write_text(renderer.render_html(record), encoding="utf-8")
    md_path.write_text(renderer.render_markdown(record), encoding="utf-8")

    sev = Counter(str(f.severity) for f in record.findings)
    confirmed = sum(1 for f in record.findings if str(f.exploitability) == "confirmed")
    print("\n✅ Готово!")
    print(f"   состояние: {record.state}")
    print("   находки: " + (", ".join(f"{k}={v}" for k, v in sev.most_common()) or "нет"))
    print(f"   🎯 подтверждённых эксплойтов (forge доказал): {confirmed}")
    print(f"\n📄 ОТЧЁТ КЛИЕНТУ:  {html_path}")
    print("   открой в браузере → Cmd+P → «Сохранить как PDF» → отправь")
    print(f"   markdown-версия:  {md_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="wr3 pre-audit report generator")
    ap.add_argument("file", help="путь к .sol файлу")
    ap.add_argument("--deep", action="store_true", help="добавить Medusa-фаззинг (медленнее)")
    ap.add_argument("--chain", default="ethereum", help="ethereum|base|bsc|arbitrum (по умолч. ethereum)")
    args = ap.parse_args()

    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        print(f"❌ Файл не найден: {path}")
        return 1
    try:
        Chain(args.chain)
    except ValueError:
        print(f"❌ Неизвестная сеть '{args.chain}'. Доступно: ethereum, base, bsc, arbitrum")
        return 1
    return asyncio.run(run(path, "deep" if args.deep else "standard", args.chain))


if __name__ == "__main__":
    raise SystemExit(main())
