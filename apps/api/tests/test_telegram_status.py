from types import SimpleNamespace

import pytest

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import CreateAuditRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.telegram_bot import TelegramCommandBot


def _bot(svc: AuditService, *, running=True, healthy=True, last_error=None) -> TelegramCommandBot:
    status = SimpleNamespace(
        running=running, healthy=healthy, cycle_count=2, drained_total=8, last_error=last_error
    )
    scout = SimpleNamespace(status=lambda: status)
    return TelegramCommandBot(audit_service=svc, scout_autopilot=scout, settings=get_settings())


@pytest.mark.asyncio
async def test_platform_counts_reflects_state():
    svc = AuditService()
    for i in range(3):
        await svc.create_audit(
            CreateAuditRequest(chain=Chain.BASE, address="0x" + f"{i + 1:040x}", source="contract C {}")
        )
    counts = svc.platform_counts()
    assert counts == {"queued": 3, "completed": 0, "confirmed": 0}


def test_status_running_shows_verdict_and_live_stats():
    out = _bot(AuditService())._cmd_status()
    assert "✅ ПЛАТФОРМА РАБОТАЕТ" in out
    assert "Подтверждённых эксплойтов: 0" in out
    assert "Проверено контрактов: 0" in out
    assert "В очереди на проверку: 0" in out


def test_status_degraded_and_off_verdicts():
    assert "🟡" in _bot(AuditService(), running=True, healthy=False)._cmd_status()
    off = _bot(AuditService(), running=False, healthy=False)._cmd_status()
    assert "🔴" in off and "ВЫКЛЮЧЕН" in off


def test_status_surfaces_last_error():
    out = _bot(AuditService(), last_error="BoomError:nope")._cmd_status()
    assert "BoomError:nope" in out
