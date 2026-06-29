from __future__ import annotations

import asyncio
import re

import httpx

from wr3_api.core.config import Settings, get_settings
from wr3_api.services.audit_service import AuditService
from wr3_api.services.scout_autopilot import ScoutAutopilot

_HELP = (
    "🤖 wr3 — команды:\n"
    "/queue — последние находки (id, проект, баг)\n"
    "/report <id> — собрать готовый отчёт для баунти\n"
    "/status — здоровье автопилота\n"
    "/help — это сообщение\n\n"
    "id берёшь из пуша или из /queue (8 символов)."
)
_ID_RE = re.compile(r"[0-9a-fA-F]{8}")


class TelegramCommandBot:
    """Inbound Telegram command bot (long-poll, no public URL needed). Replies
    only to the configured reviewer ids — the owner — so it's private."""

    def __init__(
        self,
        *,
        audit_service: AuditService,
        scout_autopilot: ScoutAutopilot | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._audit = audit_service
        self._scout = scout_autopilot
        self._offset = 0

    @property
    def _token(self) -> str | None:
        return self._settings.telegram_bot_token

    @property
    def _allowed(self) -> set[str]:
        return {str(uid) for uid in (self._settings.telegram_reviewer_user_ids or [])}

    async def run(self) -> None:
        if not self._token or not self._allowed:
            return  # not configured — no-op
        async with httpx.AsyncClient(timeout=35.0) as client:
            while True:
                try:
                    for update in await self._get_updates(client):
                        self._offset = max(self._offset, int(update.get("update_id", 0)) + 1)
                        message = update.get("message") or update.get("edited_message") or {}
                        text = (message.get("text") or "").strip()
                        chat_id = (message.get("chat") or {}).get("id")
                        from_id = str((message.get("from") or {}).get("id") or "")
                        if not text or chat_id is None:
                            continue
                        if from_id not in self._allowed:
                            await self._send(client, chat_id, "⛔ Этот бот приватный.")
                            continue
                        await self._send(client, chat_id, self._handle(text))
                except asyncio.CancelledError:
                    raise
                except Exception:
                    await asyncio.sleep(3)  # transient network/API hiccup; keep polling

    async def _get_updates(self, client: httpx.AsyncClient) -> list[dict]:
        response = await client.get(
            f"https://api.telegram.org/bot{self._token}/getUpdates",
            params={"offset": self._offset, "timeout": 25},
        )
        payload = response.json()
        return payload.get("result", []) if payload.get("ok") else []

    async def _send(self, client: httpx.AsyncClient, chat_id: int, text: str) -> None:
        for start in range(0, max(len(text), 1), 3900):  # Telegram caps messages at 4096
            await client.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                json={"chat_id": chat_id, "text": text[start : start + 3900], "disable_web_page_preview": True},
            )

    def _handle(self, text: str) -> str:
        command = text.split()[0].lower().lstrip("/")
        if command in {"report", "отчёт", "отчет", "собери"}:
            return self._cmd_report(text)
        if command in {"queue", "очередь"}:
            return self._cmd_queue()
        if command in {"status", "статус"}:
            return self._cmd_status()
        return _HELP

    def _cmd_report(self, text: str) -> str:
        match = _ID_RE.search(text)
        if not match:
            return "Укажи id: /report <id> (8 символов из пуша или /queue)."
        prefix = match.group(0).lower()
        record = self._audit.find_record_by_id_prefix(prefix)
        if record is None:
            return f"Не нашёл аудит {prefix}. Список — /queue."
        report = self._audit.bounty_submission_for(record)
        if report is None:
            return f"В аудите {prefix} нет находок для отчёта."
        return report

    def _cmd_queue(self) -> str:
        items = self._audit.candidate_queue(limit=10)
        if not items:
            return "Очередь пуста — робот пока не нашёл high/critical. Это нормально, он сканит."
        lines = ["📋 Последние находки:\n"]
        for it in items:
            mark = "✅" if it["confirmed"] else "🟡"
            program = f" · {it['program']}" if it["program"] else ""
            lines.append(f"{mark} {it['id']} · {it['chain']} · {it['severity']} · {it['bug']}{program}")
        lines.append("\nОтчёт по находке: /report <id>")
        return "\n".join(lines)

    def _cmd_status(self) -> str:
        if self._scout is None:
            return "Статус автопилота недоступен."
        s = self._scout.status()
        if s.running and s.healthy:
            verdict = "✅ ПЛАТФОРМА РАБОТАЕТ\nОхотится прямо сейчас 🛰"
        elif s.running:
            verdict = "🟡 РАБОТАЕТ ЧАСТИЧНО\nАвтопилот запущен, но нездоров"
        else:
            verdict = "🔴 АВТОПИЛОТ ВЫКЛЮЧЕН"
        lines = [verdict, ""]
        try:  # live-цифры best-effort — не ломаем статус из-за сбоя БД
            c = self._audit.platform_counts()
            lines.append(f"🎯 Подтверждённых эксплойтов: {c['confirmed']}")
            lines.append(f"📊 Проверено контрактов: {c['completed']}")
            lines.append(f"⏳ В очереди на проверку: {c['queued']}")
            lines.append("")
        except Exception:
            pass
        lines.append(f"🛰 Автопилот: цикл #{s.cycle_count} · разобрано из очереди {s.drained_total}")
        if s.last_error:
            lines.append(f"⚠️ Последняя ошибка: {s.last_error}")
        return "\n".join(lines)
