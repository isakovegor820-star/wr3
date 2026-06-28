from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from wr3_api.core.config import Settings, get_settings
from wr3_api.main import _safe_cors, create_app
from wr3_api.services.repository import _PayloadCipher

_FERNET_KEY = Fernet.generate_key().decode()


def test_safe_cors_strips_wildcard_origin_and_regex():
    settings = Settings(cors_origins=["*", "https://app.wr3.dev"], cors_origin_regex=".*")
    origins, regex = _safe_cors(settings)
    assert "*" not in origins
    assert "https://app.wr3.dev" in origins
    assert regex is None  # wildcard regex dropped so it can't pair with credentials


def test_safe_cors_keeps_explicit_origins_and_regex():
    settings = Settings(cors_origins=["https://app.wr3.dev"], cors_origin_regex=r"https://.*\.wr3\.dev")
    origins, regex = _safe_cors(settings)
    assert "https://app.wr3.dev" in origins
    assert "http://localhost:3001" in origins  # dev defaults always present
    assert regex == r"https://.*\.wr3\.dev"


def test_payload_cipher_roundtrip_hides_source():
    cipher = _PayloadCipher(_FERNET_KEY)
    payload = {"request": {"source": "contract Secret { uint256 password; }"}}
    encrypted = cipher.encrypt(payload)
    assert "wr3_enc_v1" in encrypted
    # the contract source must not appear in the at-rest blob
    assert "password" not in str(encrypted)
    assert "contract Secret" not in str(encrypted)
    assert cipher.decrypt(encrypted) == payload


def test_payload_cipher_without_key_is_plaintext_passthrough():
    cipher = _PayloadCipher(None)
    payload = {"a": 1}
    assert cipher.encrypt(payload) == payload
    assert cipher.decrypt(payload) == payload
    assert cipher.active is False


def test_telegram_emulator_header_cannot_bypass_secret_in_production(monkeypatch):
    monkeypatch.setenv("WR3_ENVIRONMENT", "production")
    monkeypatch.setenv("WR3_TELEGRAM_WEBHOOK_SECRET", "s3cret-bot-token")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        # No valid bot secret + emulator header -> must be rejected in production.
        blocked = client.post(
            "/v1/telegram/webhook", json={}, headers={"X-WR3-Local-Emulator": "true"}
        )
        assert blocked.status_code == 403
        # The real bot secret still works.
        ok = client.post(
            "/v1/telegram/webhook",
            json={},
            headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret-bot-token"},
        )
        assert ok.status_code != 403
    finally:
        get_settings.cache_clear()


def test_telegram_emulator_header_allowed_in_development(monkeypatch):
    monkeypatch.setenv("WR3_ENVIRONMENT", "development")
    monkeypatch.setenv("WR3_TELEGRAM_WEBHOOK_SECRET", "s3cret-bot-token")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        allowed = client.post(
            "/v1/telegram/webhook", json={}, headers={"X-WR3-Local-Emulator": "true"}
        )
        assert allowed.status_code != 403
    finally:
        get_settings.cache_clear()
