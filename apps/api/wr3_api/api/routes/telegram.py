from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from wr3_api.api.routes.audits import service as audit_service
from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain, UserIntent
from wr3_api.domain.schemas import CreateAuditRequest
from wr3_api.services.auth import AuthContext
from wr3_api.services.dispatcher import dispatch_audit_processing

router = APIRouter(prefix="/v1/telegram", tags=["telegram"])

SCAN_RE = re.compile(r"^/scan(?:@\w+)?\s+(?:(ethereum|base|bsc|arbitrum|solana)\s+)?(\S+)$", re.IGNORECASE)


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

    match = SCAN_RE.match(text)
    if not match:
        return {
            "ok": True,
            "reply": "Use /scan <chain> <address>. Supported chains: ethereum, base, bsc, arbitrum, solana.",
        }

    chain_text = (match.group(1) or "base").lower()
    address = match.group(2)
    request = CreateAuditRequest(
        chain=Chain(chain_text),
        address=address,
        requested_depth="preliminary",
        visibility="private",
        user_intent=UserIntent.THIRD_PARTY_RESEARCH,
    )
    actor = AuthContext(
        user_id=f"telegram:{telegram_user_id}",
        provider="telegram",
        subject=telegram_user_id,
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
        "reply": f"wr3 scan queued for {chain_text}. Status: {status_url}",
        "audit_id": str(record.audit_id),
        "state": record.state,
        "status_url": status_url,
        "limitations": record.limitations,
    }
