"""Regression tests for the security-hardening review fixes (H1, H3, H4, H5)."""
import pytest
from fastapi.testclient import TestClient

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import CreateAuditRequest
from wr3_api.main import create_app
from wr3_api.services.audit_service import AuditService
from wr3_api.services.report_renderer import ReportRenderer
from wr3_api.services.repository import _PayloadCipher
from wr3_api.services.tool_paths import tool_subprocess_env


# ---- H1: secrets never reach the untrusted-code subprocess env ----------------
def test_tool_subprocess_env_strips_all_secrets(monkeypatch):
    secrets = {
        "WR3_NAVY_API_KEY": "k",
        "WR3_ARTIFACT_ENCRYPTION_KEY": "k",
        "BACKUP_PASSPHRASE": "p",                 # escaped the old PASSWORD marker
        "CELERY_RESULT_BACKEND": "redis://u:p@h", # escaped the old markers
        "R2_URI": "https://key:secret@r2",        # escaped: URI not _URL
        "AWS_SECRET_ACCESS_KEY": "k",
        "DATABASE_URL": "postgres://u:p@h/db",
    }
    for key, value in secrets.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("HOME", "/home/x")

    env = tool_subprocess_env()

    for key in secrets:
        assert key not in env, f"{key} leaked into the engine subprocess env"
    assert "PATH" in env and "HOME" in env  # benign vars still pass through


# ---- H3: encryption fails closed when required (prod), lenient in dev ----------
def test_payload_cipher_fail_closed_when_required():
    with pytest.raises(RuntimeError):
        _PayloadCipher(None, require=True)
    with pytest.raises(RuntimeError):
        _PayloadCipher("", require=True)
    lenient = _PayloadCipher(None, require=False)  # dev: plaintext allowed, no raise
    assert lenient.active is False


# ---- H4: HTML report escapes attacker-controlled text (stored XSS) -------------
@pytest.mark.asyncio
async def test_render_html_escapes_attacker_controlled_text():
    svc = AuditService()
    rec = await svc.create_audit(
        CreateAuditRequest(chain=Chain.BASE, address="0x" + "3" * 40, source="contract C {}")
    )
    await svc.process_audit(rec.audit_id)
    record = svc.get_record(rec.audit_id)
    record.request.address = "<script>alert('xss')</script>"  # attacker-controlled

    out = ReportRenderer().render_html(record)

    assert "<script>alert('xss')</script>" not in out  # not injected raw
    assert "&lt;script&gt;" in out                      # present, but escaped


# ---- H5: webhook fails closed outside development ------------------------------
def test_webhook_requires_secret_outside_development(monkeypatch):
    monkeypatch.setenv("WR3_ENVIRONMENT", "production")
    monkeypatch.delenv("WR3_TELEGRAM_WEBHOOK_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        body = {"message": {"text": "/status", "from": {"id": 1}, "chat": {"id": 1}}}
        # No secret configured/sent -> rejected (the old code skipped the check).
        assert client.post("/v1/telegram/webhook", json=body).status_code == 403
        # The local-emulator bypass is ignored in production -> still rejected.
        assert (
            client.post(
                "/v1/telegram/webhook", headers={"X-WR3-Local-Emulator": "true"}, json=body
            ).status_code
            == 403
        )
    finally:
        get_settings.cache_clear()
