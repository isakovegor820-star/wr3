from fastapi.testclient import TestClient

from wr3_api.api.routes import telegram as telegram_routes
from wr3_api.core.config import get_settings
from wr3_api.main import create_app


client = TestClient(create_app())
LOCAL_TELEGRAM_HEADERS = {"X-WR3-Local-Emulator": "true"}


def test_telegram_scan_command_queues_audit():
    response = client.post(
        "/v1/telegram/webhook",
        headers=LOCAL_TELEGRAM_HEADERS,
        json={
            "message": {
                "text": "/scan base 0x0000000000000000000000000000000000000000",
                "from": {"id": 1508},
                "chat": {"id": 1508},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["state"] == "queued"
    assert "/audits/" in payload["status_url"]
    assert any("third_party_scan_public_poc_disabled" in item for item in payload["limitations"])


def test_telegram_unknown_command_returns_help():
    response = client.post(
        "/v1/telegram/webhook",
        headers=LOCAL_TELEGRAM_HEADERS,
        json={"message": {"text": "/help", "from": {"id": 1508}, "chat": {"id": 1508}}},
    )

    assert response.status_code == 200
    assert "Используй /scan" in response.json()["reply"]


def test_telegram_webhook_sends_real_chat_reply_when_token_configured(monkeypatch):
    sent: list[tuple[str, dict[str, object]]] = []

    async def fake_post_telegram_method(token: str, method: str, payload: dict[str, object]) -> None:
        sent.append((method, payload))

    monkeypatch.setattr(get_settings(), "telegram_bot_token", "123:test")
    monkeypatch.setattr(get_settings(), "telegram_webhook_secret", "secret")
    monkeypatch.setattr(telegram_routes, "_post_telegram_method", fake_post_telegram_method)

    response = client.post(
        "/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
        json={"message": {"text": "/start", "from": {"id": 1508}, "chat": {"id": 1508}}},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert sent == [
        (
            "sendMessage",
            {
                "chat_id": 1508,
                "text": response.json()["reply"],
                "disable_web_page_preview": True,
            },
        )
    ]


def test_telegram_watch_command_creates_watchlist_entry():
    response = client.post(
        "/v1/telegram/webhook",
        headers=LOCAL_TELEGRAM_HEADERS,
        json={
            "message": {
                "text": "/watch base 0x0000000000000000000000000000000000000000 demo",
                "from": {"id": 1508},
                "chat": {"id": 1508},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["watchlist_entry"]["chain"] == "base"
    assert payload["watchlist_entry"]["label"] == "demo"


def test_telegram_score_command_returns_public_project_summary():
    response = client.post(
        "/v1/telegram/webhook",
        headers=LOCAL_TELEGRAM_HEADERS,
        json={
            "message": {
                "text": "/score base 0x0000000000000000000000000000000000000000",
                "from": {"id": 1508},
                "chat": {"id": 1508},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "wr3 оценка" in payload["reply"]
    assert payload["project"]["chain"] == "base"
