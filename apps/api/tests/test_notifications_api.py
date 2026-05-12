from fastapi.testclient import TestClient

from wr3_api.main import create_app


client = TestClient(create_app())


def test_watchlist_requires_auth_and_creates_stub():
    forbidden = client.post(
        "/v1/watchlist",
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000000",
        },
    )
    assert forbidden.status_code == 403

    response = client.post(
        "/v1/watchlist",
        headers={"X-WR3-User": "watcher"},
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000000",
            "label": "Vault",
            "alert_channels": ["telegram"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "active"
    assert "monitoring_worker_not_enabled_in_local_mvp" in payload["limitations"]


def test_webhook_test_is_safe_stub():
    response = client.post(
        "/v1/webhooks/test",
        headers={"X-WR3-User": "watcher"},
        json={"url": "https://example.com/wr3-hook", "event_type": "wr3.test"},
    )

    assert response.status_code == 200
    assert response.json()["delivered"] is False
    assert response.json()["payload_preview"]["data"]["contains_private_findings"] is False
    assert "private_findings_never_sent_in_test_payload" in response.json()["limitations"]
    assert "webhook_delivery_disabled_dry_run" in response.json()["limitations"]
