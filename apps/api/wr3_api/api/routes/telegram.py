from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from wr3_api.api.routes.audits import service as audit_service
from wr3_api.api.routes.notifications import service as notification_service
from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain, UserIntent
from wr3_api.domain.schemas import CreateAuditRequest, WatchlistRequest
from wr3_api.services.auth import AuthContext
from wr3_api.services.dispatcher import dispatch_audit_processing

router = APIRouter(prefix="/v1/telegram", tags=["telegram"])

SCAN_RE = re.compile(r"^/scan(?:@\w+)?\s+(?:(ethereum|base|bsc|arbitrum|solana)\s+)?(\S+)$", re.IGNORECASE)
WATCH_RE = re.compile(r"^/watch(?:@\w+)?\s+(?:(ethereum|base|bsc|arbitrum|solana)\s+)?(\S+)(?:\s+(.+))?$", re.IGNORECASE)
SCORE_RE = re.compile(r"^/score(?:@\w+)?\s+(?:(ethereum|base|bsc|arbitrum|solana)\s+)?(\S+)$", re.IGNORECASE)


@router.post("/webhook")
async def telegram_webhook(
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    settings = get_settings()
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="telegram_webhook_secret_mismatch")

    message = update.get("message") or update.get("edited_message") or {}
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    telegram_user_id = str(sender.get("id") or chat.get("id") or "anonymous")

    actor = AuthContext(
        user_id=f"telegram:{telegram_user_id}",
        provider="telegram",
        subject=telegram_user_id,
    )

    watch_match = WATCH_RE.match(text)
    if watch_match:
        chain_text = (watch_match.group(1) or "base").lower()
        address = watch_match.group(2)
        label = watch_match.group(3) or None
        entry = notification_service.add_watchlist_entry(
            WatchlistRequest(
                chain=Chain(chain_text),
                address=address,
                label=label,
                alert_channels=["telegram"],
            ),
            actor,
        )
        return {
            "ok": True,
            "reply": f"wr3 включил алерты для {chain_text}:{address}. Запись: {entry.id}",
            "watchlist_entry": entry,
        }

    score_match = SCORE_RE.match(text)
    if score_match:
        chain_text = (score_match.group(1) or "base").lower()
        address = score_match.group(2)
        project = audit_service.public_project(Chain(chain_text), address)
        score = project.score.final_score if project.score else "публичной оценки пока нет"
        return {
            "ok": True,
            "reply": f"wr3 оценка для {chain_text}:{address}: {score}. Публичные находки: {len(project.public_findings)}.",
            "project": project,
        }

    scan_match = SCAN_RE.match(text)
    if not scan_match:
        return {
            "ok": True,
            "reply": "Используй /scan <сеть> <адрес>, /watch <сеть> <адрес> или /score <сеть> <адрес>. Поддерживаются: ethereum, base, bsc, arbitrum, solana.",
        }

    chain_text = (scan_match.group(1) or "base").lower()
    address = scan_match.group(2)
    request = CreateAuditRequest(
        chain=Chain(chain_text),
        address=address,
        requested_depth="preliminary",
        visibility="private",
        user_intent=UserIntent.THIRD_PARTY_RESEARCH,
    )
    record = await audit_service.create_audit(request, actor)
    record.limitations.extend(
        dispatch_audit_processing(
            audit_id=record.audit_id,
            background_tasks=background_tasks,
            local_processor=audit_service.process_audit,
        )
    )
    status_url = f"{settings.web_base_url}/audits/{record.audit_id}?owner_token={record.owner_access_token}"
    return {
        "ok": True,
        "reply": f"wr3 поставил скан {chain_text} в очередь. Статус: {status_url}",
        "audit_id": str(record.audit_id),
        "state": record.state,
        "status_url": status_url,
        "limitations": record.limitations,
    }
