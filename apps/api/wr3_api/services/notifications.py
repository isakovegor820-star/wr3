from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Awaitable, Callable

import httpx

from wr3_api.core.config import get_settings
from wr3_api.domain.schemas import (
    DisclosurePacketResponse,
    WatchlistEntry,
    WatchlistRequest,
    WebhookTestRequest,
    WebhookTestResponse,
)
from wr3_api.services.auth import AuthContext


class NotificationAccessDenied(PermissionError):
    pass


WebhookSender = Callable[[str, dict[str, object], dict[str, str]], Awaitable[int]]


class NotificationService:
    def __init__(self, sender: WebhookSender | None = None) -> None:
        self._watchlist: dict[str, WatchlistEntry] = {}
        self._sender = sender or self._send_http_webhook

    def add_watchlist_entry(self, request: WatchlistRequest, actor: AuthContext) -> WatchlistEntry:
        if not actor.is_authenticated or actor.user_id is None:
            raise NotificationAccessDenied("authenticated_user_required_for_watchlist")
        entry = WatchlistEntry(
            user_id=actor.user_id,
            chain=request.chain,
            address=request.address,
            label=request.label,
            alert_channels=request.alert_channels,
            limitations=["monitoring_worker_not_enabled_in_local_mvp"],
        )
        self._watchlist[entry.id] = entry
        return entry

    async def test_webhook(self, request: WebhookTestRequest, actor: AuthContext) -> WebhookTestResponse:
        if not actor.is_authenticated or actor.user_id is None:
            raise NotificationAccessDenied("authenticated_user_required_for_webhook_test")
        payload = self.build_safe_test_payload(request, actor)
        signature = self.sign_payload(payload)
        limitations = ["private_findings_never_sent_in_test_payload"]
        delivered = False
        settings = get_settings()
        if settings.webhook_delivery_enabled:
            headers = self.build_delivery_headers(signature)
            try:
                status_code = await self._sender(request.url, payload, headers)
                delivered = 200 <= status_code < 300
                if not delivered:
                    limitations.append(f"webhook_delivery_non_2xx:{status_code}")
            except Exception as exc:
                limitations.append(f"webhook_delivery_error:{exc.__class__.__name__}")
        else:
            limitations.append("webhook_delivery_disabled_dry_run")
        return WebhookTestResponse(
            delivered=delivered,
            event_type=request.event_type,
            payload_preview=payload,
            signature=signature,
            limitations=limitations,
        )

    def build_safe_test_payload(
        self,
        request: WebhookTestRequest,
        actor: AuthContext,
    ) -> dict[str, object]:
        return {
            "event_type": request.event_type,
            "source": "wr3",
            "user_id": actor.user_id,
            "data": {
                "message": "wr3 webhook test",
                "contains_private_findings": False,
                "contains_source": False,
                "contains_poc": False,
            },
        }

    def sign_payload(self, payload: dict[str, object]) -> str | None:
        secret = get_settings().webhook_signing_secret
        if not secret:
            return None
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    def build_delivery_headers(self, signature: str | None) -> dict[str, str]:
        headers = {
            "content-type": "application/json",
            "user-agent": "wr3-webhook/0.1",
            "x-wr3-event-source": "wr3",
        }
        if signature:
            headers["x-wr3-signature-sha256"] = signature
        return headers

    def build_telegram_disclosure_alert(
        self,
        packet: DisclosurePacketResponse,
        *,
        mode: str = "normal",
    ) -> dict[str, object] | None:
        if mode not in {"normal", "ops"}:
            raise ValueError("unsupported_telegram_alert_mode")
        almost_ready = (
            packet.needs_human_approval
            and packet.confirmed_by_poc
            and packet.pdfs_generated
            and bool(packet.official_contact)
        )
        approved = packet.approved_to_contact and bool(packet.official_contact)
        if mode == "normal" and not (almost_ready or approved):
            return None

        if approved:
            text = self._approved_to_contact_text(packet)
            buttons = self._review_buttons(packet)
            buttons.append([{"text": "Отправил", "callback_data": f"wr3:sent:{packet.case_id}"}])
            kind = "approved_to_contact"
        elif almost_ready:
            text = self._almost_ready_text(packet)
            buttons = self._review_buttons(packet)
            buttons.append(
                [
                    {"text": "Approve", "callback_data": f"wr3:approve:{packet.case_id}"},
                    {"text": "Needs Review", "callback_data": f"wr3:needs_review:{packet.case_id}"},
                    {"text": "Dismiss", "callback_data": f"wr3:dismiss:{packet.case_id}"},
                ]
            )
            kind = "needs_human_approval"
        else:
            text = self._ops_context_text(packet)
            buttons = self._review_buttons(packet)
            buttons.append(
                [
                    {"text": "Needs Review", "callback_data": f"wr3:needs_review:{packet.case_id}"},
                    {"text": "Dismiss", "callback_data": f"wr3:dismiss:{packet.case_id}"},
                ]
            )
            kind = "ops_context"

        return {
            "kind": kind,
            "mode": mode,
            "case_id": packet.case_id,
            "text": text,
            "links": {
                "web_card": packet.web_url,
                "internal_pdf": packet.internal_pdf_url,
                "external_pdf": packet.external_pdf_url,
            },
            "reply_markup": {"inline_keyboard": buttons},
            "contains_private_poc": False,
            "auto_sends_external_message": False,
        }

    def build_telegram_ops_alert(self, *, title: str, detail: str, severity: str = "info") -> dict[str, object]:
        return {
            "kind": "ops",
            "severity": severity,
            "text": f"wr3 ops: {title}\n{detail}",
            "reply_markup": {"inline_keyboard": []},
            "auto_sends_external_message": False,
        }

    def _review_buttons(self, packet: DisclosurePacketResponse) -> list[list[dict[str, str]]]:
        if packet.web_url:
            return [[{"text": "Open Review", "url": packet.web_url}]]
        return [[{"text": "Open Review", "callback_data": f"wr3:open:{packet.case_id}"}]]

    def _almost_ready_text(self, packet: DisclosurePacketResponse) -> str:
        return "\n".join(
            [
                "wr3: почти готово к human review",
                f"Project: {packet.project_name or 'unknown'}",
                f"Target: {packet.chain}:{packet.address or 'source-only'}",
                f"Bug: {packet.bug_type or 'unknown'} / {packet.severity or 'unknown'}",
                f"Where: {packet.location_label or 'architecture/business logic'}",
                f"Why confident: {self._compact(packet.confidence_reason)}",
                f"Why bounty may accept: {self._compact(packet.bounty_acceptance_reason)}",
                f"Official contact: {packet.official_contact} ({packet.contact_source})",
                "Telegram omits reproduction recipes and raw private traces.",
            ]
        )

    def _ops_context_text(self, packet: DisclosurePacketResponse) -> str:
        return "\n".join(
            [
                "wr3 ops: disclosure case не готов к отправке",
                f"Readiness: {packet.readiness_state}",
                f"Project: {packet.project_name or 'unknown'}",
                f"Target: {packet.chain}:{packet.address or 'source-only'}",
                f"Contact: {packet.official_contact or 'not confirmed'} ({packet.contact_source or 'unknown'})",
                f"Limitations: {self._compact('; '.join(packet.limitations), limit=420)}",
                "Normal Telegram mode will stay quiet until PoC/fork/test, PDFs and official contact are ready.",
            ]
        )

    def _approved_to_contact_text(self, packet: DisclosurePacketResponse) -> str:
        return "\n".join(
            [
                "wr3: можно писать вручную",
                f"Official contact: {packet.official_contact} ({packet.contact_source})",
                f"External PDF: {packet.external_pdf_url}",
                "",
                "Safe draft:",
                self._compact(packet.draft_message, limit=900),
                "",
                "wr3 will only log the manual send. It will not send email/forms automatically.",
            ]
        )

    def _compact(self, value: str | None, *, limit: int = 260) -> str:
        if not value:
            return "not available"
        normalized = " ".join(value.split())
        return normalized if len(normalized) <= limit else f"{normalized[:limit - 1]}…"

    async def _send_http_webhook(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
    ) -> int:
        async with httpx.AsyncClient(timeout=get_settings().webhook_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
        return response.status_code
