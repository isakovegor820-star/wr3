from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Awaitable, Callable

import httpx

from wr3_api.core.config import get_settings
from wr3_api.domain.schemas import (
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
            limitations=["paid_tier_enforcement_pending", "monitoring_worker_not_enabled_in_local_mvp"],
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

    async def _send_http_webhook(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
    ) -> int:
        async with httpx.AsyncClient(timeout=get_settings().webhook_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
        return response.status_code
