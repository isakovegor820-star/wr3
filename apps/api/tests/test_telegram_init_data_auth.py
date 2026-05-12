import hashlib
import hmac
import json
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from wr3_api.core.config import get_settings
from wr3_api.domain.schemas import utc_now
from wr3_api.main import create_app


client = TestClient(create_app())


def signed_init_data(bot_token: str, *, user_id: int = 1508, auth_date: int | None = None) -> str:
    pairs = {
        "auth_date": str(auth_date or int(utc_now().timestamp())),
        "query_id": "wr3-test",
        "user": json.dumps({"id": user_id, "username": "wr3dev"}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(pairs)


def test_telegram_init_data_requires_explicit_account_consent(monkeypatch):
    monkeypatch.setenv("WR3_TELEGRAM_BOT_TOKEN", "123:test")
    get_settings.cache_clear()

    response = client.post(
        "/v1/auth/telegram/init-data",
        json={"init_data": signed_init_data("123:test"), "explicit_account_consent": False},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "telegram_account_consent_required"
    get_settings.cache_clear()


def test_telegram_init_data_issues_verified_session(monkeypatch):
    monkeypatch.setenv("WR3_TELEGRAM_BOT_TOKEN", "123:test")
    get_settings.cache_clear()

    response = client.post(
        "/v1/auth/telegram/init-data",
        json={"init_data": signed_init_data("123:test"), "explicit_account_consent": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "telegram"
    assert payload["subject"] == "1508"
    assert "telegram_init_data_verified" in payload["limitations"]
    get_settings.cache_clear()


def test_telegram_init_data_rejects_bad_hash(monkeypatch):
    monkeypatch.setenv("WR3_TELEGRAM_BOT_TOKEN", "123:test")
    get_settings.cache_clear()

    response = client.post(
        "/v1/auth/telegram/init-data",
        json={"init_data": signed_init_data("wrong-token"), "explicit_account_consent": True},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "telegram_init_data_hash_mismatch"
    get_settings.cache_clear()
