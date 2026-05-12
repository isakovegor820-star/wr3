import pytest

from wr3_api.core.config import get_settings
from wr3_api.domain.schemas import WebhookTestRequest
from wr3_api.services.auth import AuthContext
from wr3_api.services.notifications import NotificationService


def test_webhook_payload_signature_is_stable(monkeypatch):
    monkeypatch.setenv("WR3_WEBHOOK_SIGNING_SECRET", "secret")
    get_settings.cache_clear()
    service = NotificationService()
    actor = AuthContext(user_id="dev:watcher", provider="dev-header", subject="watcher")
    payload = service.build_safe_test_payload(WebhookTestRequest(url="https://example.com/hook"), actor)

    first = service.sign_payload(payload)
    second = service.sign_payload(payload)

    assert first == second
    assert first is not None
    assert len(first) == 64
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_webhook_delivery_uses_signed_safe_payload_when_enabled(monkeypatch):
    calls = []

    async def fake_sender(url, payload, headers):
        calls.append((url, payload, headers))
        return 204

    monkeypatch.setenv("WR3_WEBHOOK_DELIVERY_ENABLED", "true")
    monkeypatch.setenv("WR3_WEBHOOK_SIGNING_SECRET", "secret")
    get_settings.cache_clear()
    service = NotificationService(sender=fake_sender)
    actor = AuthContext(user_id="dev:watcher", provider="dev-header", subject="watcher")

    response = await service.test_webhook(WebhookTestRequest(url="https://example.com/hook"), actor)

    assert response.delivered is True
    assert len(calls) == 1
    assert calls[0][0] == "https://example.com/hook"
    assert calls[0][1]["data"]["contains_private_findings"] is False
    assert "x-wr3-signature-sha256" in calls[0][2]
    get_settings.cache_clear()
