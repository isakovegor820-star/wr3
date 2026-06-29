import pytest

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import AuditState, Chain
from wr3_api.domain.schemas import CreateAuditRequest, ScoutAutopilotRunRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.scout_autopilot import ScoutAutopilot


class _EmptyDiscovery:
    async def discover_immunefi_targets(self, **_kwargs):
        return []

    async def discover_all_supported_networks(self, **_kwargs):
        return []


def _autopilot() -> ScoutAutopilot:
    return ScoutAutopilot(audit_service=AuditService(), discovery_service=_EmptyDiscovery())


async def _make_queued(service: AuditService, n: int) -> list:
    ids = []
    for i in range(n):
        record = await service.create_audit(
            CreateAuditRequest(chain=Chain.BASE, address="0x" + f"{i + 1:040x}", source="contract C {}")
        )
        assert service.get_record(record.audit_id).state == AuditState.QUEUED
        ids.append(record.audit_id)
    return ids


@pytest.mark.asyncio
async def test_drain_schedules_queued_audits_up_to_limit(monkeypatch):
    monkeypatch.setenv("WR3_SCOUT_AUTOPILOT_DRAIN_LIMIT", "3")
    get_settings.cache_clear()
    autopilot = _autopilot()
    ids = await _make_queued(autopilot._audit_service, 5)

    scheduled: list = []
    autopilot._schedule_processing = lambda audit_id: scheduled.append(audit_id)  # type: ignore[method-assign]

    drained = await autopilot._drain_standing_queue(ScoutAutopilotRunRequest(process_queued=True))

    assert drained == 3  # capped at the per-cycle budget
    assert len(scheduled) == 3
    assert set(scheduled).issubset(set(ids))  # only real queued ids, oldest first
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_drain_is_noop_when_process_queued_false():
    autopilot = _autopilot()
    await _make_queued(autopilot._audit_service, 3)
    scheduled: list = []
    autopilot._schedule_processing = lambda audit_id: scheduled.append(audit_id)  # type: ignore[method-assign]

    drained = await autopilot._drain_standing_queue(ScoutAutopilotRunRequest(process_queued=False))

    assert drained == 0
    assert scheduled == []


@pytest.mark.asyncio
async def test_drain_skips_ids_already_in_flight():
    autopilot = _autopilot()
    ids = await _make_queued(autopilot._audit_service, 3)
    autopilot._inflight.add(ids[0])  # already being processed -> must not double-schedule
    scheduled: list = []
    autopilot._schedule_processing = lambda audit_id: scheduled.append(audit_id)  # type: ignore[method-assign]

    drained = await autopilot._drain_standing_queue(ScoutAutopilotRunRequest(process_queued=True))

    assert ids[0] not in scheduled
    assert drained == 2
    assert set(scheduled) == {ids[1], ids[2]}
