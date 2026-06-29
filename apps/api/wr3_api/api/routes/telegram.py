from __future__ import annotations

import re
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query

from wr3_api.api.dependencies import get_optional_auth
from wr3_api.api.routes.audits import service as audit_service
from wr3_api.api.routes.notifications import service as notification_service
from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain, UserIntent
from wr3_api.domain.schemas import (
    CreateAuditRequest,
    DisclosureManualSentRequest,
    DisclosurePacketActionRequest,
    WatchlistRequest,
)
from wr3_api.services.audit_service import AuditAccessDenied, AuditNotFound
from wr3_api.services.auth import AuthContext
from wr3_api.services.dispatcher import dispatch_audit_processing

router = APIRouter(prefix="/v1/telegram", tags=["telegram"])

SCAN_RE = re.compile(r"^/scan(?:@\w+)?\s+(?:(ethereum|base|bsc|arbitrum|solana)\s+)?(\S+)$", re.IGNORECASE)
WATCH_RE = re.compile(r"^/watch(?:@\w+)?\s+(?:(ethereum|base|bsc|arbitrum|solana)\s+)?(\S+)(?:\s+(.+))?$", re.IGNORECASE)
SCORE_RE = re.compile(r"^/score(?:@\w+)?\s+(?:(ethereum|base|bsc|arbitrum|solana)\s+)?(\S+)$", re.IGNORECASE)


@router.get("/disclosure-alerts")
async def telegram_disclosure_alerts(
    mode: str = Query(default="normal", pattern="^(normal|ops)$"),
    actor: AuthContext = Depends(get_optional_auth),
):
    if not actor.is_reviewer:
        raise HTTPException(status_code=403, detail="reviewer_access_required_for_telegram_disclosure_alerts")
    alerts: list[dict[str, object]] = []
    for case in audit_service.list_disclosure_cases(actor):
        packet = audit_service.get_disclosure_packet(case.id, actor)
        alert = notification_service.build_telegram_disclosure_alert(packet, mode=mode)
        if alert is not None:
            alerts.append(alert)
    if mode == "ops":
        alerts.append(
            notification_service.build_telegram_ops_alert(
                title="daily summary",
                detail=f"{len(alerts)} disclosure alerts ready for review/contact logging.",
            )
        )
    return {"ok": True, "mode": mode, "alerts": alerts}


@router.post("/webhook")
async def telegram_webhook(
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    x_wr3_local_emulator: str | None = Header(default=None),
):
    settings = get_settings()
    # The local emulator header may only bypass the webhook secret in development.
    # In production it is ignored, so a real bot secret is always required.
    is_local_emulator = x_wr3_local_emulator == "true" and settings.environment == "development"
    secret_ok = bool(settings.telegram_webhook_secret) and (
        x_telegram_bot_api_secret_token == settings.telegram_webhook_secret
    )
    # Fail closed: outside development a matching webhook secret is mandatory — an
    # UNSET secret must not silently disable auth (otherwise anyone can drive
    # disclosure actions by spoofing from.id). In development we stay lenient so the
    # emulator/local testing keeps working without configuring a secret.
    if not secret_ok and not is_local_emulator:
        if settings.environment != "development":
            raise HTTPException(status_code=403, detail="telegram_webhook_secret_required")
        if settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="telegram_webhook_secret_mismatch")
    delivery_enabled = bool(settings.telegram_bot_token) and not is_local_emulator and (
        not settings.telegram_webhook_secret or secret_ok
    )

    callback = update.get("callback_query") or {}
    if callback:
        return _handle_disclosure_callback(callback, settings, background_tasks, delivery_enabled)

    message = update.get("message") or update.get("edited_message") or {}
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
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
        reply = f"wr3 включил алерты для {chain_text}:{address}. Запись: {entry.id}"
        _queue_telegram_message(background_tasks, settings, delivery_enabled, chat_id, reply)
        return {
            "ok": True,
            "reply": reply,
            "watchlist_entry": entry,
        }

    score_match = SCORE_RE.match(text)
    if score_match:
        chain_text = (score_match.group(1) or "base").lower()
        address = score_match.group(2)
        project = audit_service.public_project(Chain(chain_text), address)
        score = project.score.final_score if project.score else "публичной оценки пока нет"
        reply = f"wr3 оценка для {chain_text}:{address}: {score}. Публичные находки: {len(project.public_findings)}."
        _queue_telegram_message(background_tasks, settings, delivery_enabled, chat_id, reply)
        return {
            "ok": True,
            "reply": reply,
            "project": project,
        }

    scan_match = SCAN_RE.match(text)
    if not scan_match:
        reply = (
            "Используй /scan <сеть> <адрес>, /watch <сеть> <адрес> или /score <сеть> <адрес>. "
            "Поддерживаются: ethereum, base, bsc, arbitrum, solana."
        )
        _queue_telegram_message(background_tasks, settings, delivery_enabled, chat_id, reply)
        return {
            "ok": True,
            "reply": reply,
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
    reply = f"wr3 поставил скан {chain_text} в очередь. Статус: {status_url}"
    _queue_telegram_message(background_tasks, settings, delivery_enabled, chat_id, reply)
    return {
        "ok": True,
        "reply": reply,
        "audit_id": str(record.audit_id),
        "state": record.state,
        "status_url": status_url,
        "limitations": record.limitations,
    }


def _handle_disclosure_callback(
    callback: dict[str, Any],
    settings: Any,
    background_tasks: BackgroundTasks,
    delivery_enabled: bool,
) -> dict[str, Any]:
    sender = callback.get("from") or {}
    telegram_user_id = str(sender.get("id") or "").strip()
    callback_id = str(callback.get("id") or "").strip()
    callback_message = callback.get("message") or {}
    chat = callback_message.get("chat") or {}
    chat_id = chat.get("id") or telegram_user_id or None
    actor = AuthContext(
        user_id=f"telegram:{telegram_user_id}" if telegram_user_id else "telegram:anonymous",
        provider="telegram",
        subject=telegram_user_id or "anonymous",
        is_reviewer=telegram_user_id in {str(item) for item in settings.telegram_reviewer_user_ids},
    )
    data = str(callback.get("data") or "").strip()
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "wr3":
        reply = "wr3 получил callback, но не знает это действие."
        _queue_telegram_callback_answer(background_tasks, settings, delivery_enabled, callback_id, reply)
        return {"ok": True, "reply": reply, "ignored": True}

    action, case_id = parts[1], parts[2]
    try:
        if action == "approve":
            packet = audit_service.approve_disclosure_packet(
                case_id,
                DisclosurePacketActionRequest(note=f"telegram approve by {actor.subject}"),
                actor,
            )
            reply = "wr3 отметил approve. Теперь можно писать вручную в официальный канал."
            alert = notification_service.build_telegram_disclosure_alert(packet, mode="normal")
            _queue_telegram_callback_answer(background_tasks, settings, delivery_enabled, callback_id, reply)
            if alert:
                _queue_telegram_message(
                    background_tasks,
                    settings,
                    delivery_enabled,
                    chat_id,
                    str(alert["text"]),
                    reply_markup=alert.get("reply_markup") if isinstance(alert.get("reply_markup"), dict) else None,
                )
            return {
                "ok": True,
                "action": action,
                "case_id": case_id,
                "reply": reply,
                "packet": packet,
                "telegram_alert": alert,
                "auto_sends_external_message": False,
            }
        if action == "needs_review":
            packet = audit_service.request_more_disclosure_review(
                case_id,
                DisclosurePacketActionRequest(note=f"telegram needs-review by {actor.subject}"),
                actor,
            )
            reply = "wr3 вернул кейс в ручную проверку. Normal Telegram mode больше не будет пушить его как готовый."
            _queue_telegram_callback_answer(background_tasks, settings, delivery_enabled, callback_id, reply)
            _queue_telegram_message(background_tasks, settings, delivery_enabled, chat_id, reply)
            return {
                "ok": True,
                "action": action,
                "case_id": case_id,
                "reply": reply,
                "packet": packet,
                "auto_sends_external_message": False,
            }
        if action == "dismiss":
            packet = audit_service.dismiss_disclosure_packet(
                case_id,
                DisclosurePacketActionRequest(note=f"telegram dismiss by {actor.subject}"),
                actor,
            )
            reply = "wr3 закрыл disclosure packet как dismissed."
            _queue_telegram_callback_answer(background_tasks, settings, delivery_enabled, callback_id, reply)
            _queue_telegram_message(background_tasks, settings, delivery_enabled, chat_id, reply)
            return {
                "ok": True,
                "action": action,
                "case_id": case_id,
                "reply": reply,
                "packet": packet,
                "auto_sends_external_message": False,
            }
        if action == "sent":
            packet = audit_service.mark_disclosure_manually_sent(
                case_id,
                DisclosureManualSentRequest(
                    channel="manual_telegram_ack",
                    note=f"operator confirmed manual send in Telegram: {actor.subject}",
                ),
                actor,
            )
            reply = "wr3 только залогировал ручную отправку. Email/forms не отправлялись автоматически."
            _queue_telegram_callback_answer(background_tasks, settings, delivery_enabled, callback_id, reply)
            _queue_telegram_message(background_tasks, settings, delivery_enabled, chat_id, reply)
            return {
                "ok": True,
                "action": action,
                "case_id": case_id,
                "reply": reply,
                "packet": packet,
                "auto_sends_external_message": False,
            }
        if action == "open":
            packet = audit_service.get_disclosure_packet(case_id, actor)
            reply = packet.web_url or settings.web_base_url
            _queue_telegram_callback_answer(background_tasks, settings, delivery_enabled, callback_id, reply)
            return {
                "ok": True,
                "action": action,
                "case_id": case_id,
                "reply": reply,
                "packet": packet,
                "auto_sends_external_message": False,
            }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    reply = "wr3 получил callback, но действие пока не поддерживается."
    _queue_telegram_callback_answer(background_tasks, settings, delivery_enabled, callback_id, reply)
    return {"ok": True, "reply": reply, "ignored": True}


def _queue_telegram_message(
    background_tasks: BackgroundTasks,
    settings: Any,
    delivery_enabled: bool,
    chat_id: object,
    text: str,
    *,
    reply_markup: dict[str, object] | None = None,
) -> None:
    if not delivery_enabled or not settings.telegram_bot_token or chat_id in {None, ""}:
        return
    payload: dict[str, object] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    background_tasks.add_task(_post_telegram_method, settings.telegram_bot_token, "sendMessage", payload)


def _queue_telegram_callback_answer(
    background_tasks: BackgroundTasks,
    settings: Any,
    delivery_enabled: bool,
    callback_id: str,
    text: str,
) -> None:
    if not delivery_enabled or not settings.telegram_bot_token or not callback_id:
        return
    background_tasks.add_task(
        _post_telegram_method,
        settings.telegram_bot_token,
        "answerCallbackQuery",
        {"callback_query_id": callback_id, "text": text[:190], "show_alert": False},
    )


async def _post_telegram_method(token: str, method: str, payload: dict[str, object]) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"https://api.telegram.org/bot{token}/{method}", json=payload)
    except Exception:
        # Telegram delivery is best-effort; the webhook response still keeps the local emulator useful.
        return
