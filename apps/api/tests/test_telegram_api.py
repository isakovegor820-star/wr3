from fastapi.testclient import TestClient

from wr3_api.main import create_app


client = TestClient(create_app())


def test_telegram_scan_command_queues_audit():
    response = client.post(
        "/v1/telegram/webhook",
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
        json={"message": {"text": "/help", "from": {"id": 1508}, "chat": {"id": 1508}}},
    )

    assert response.status_code == 200
    assert "Используй /scan" in response.json()["reply"]


def test_telegram_watch_command_creates_watchlist_entry():
    response = client.post(
        "/v1/telegram/webhook",
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
