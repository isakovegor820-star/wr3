import asyncio
from datetime import timedelta

import pytest

from wr3_api.domain.schemas import utc_now
from wr3_api.services.audit_service import AuditService
from wr3_api.services.scout_autopilot import ScoutAutopilot


class _StubNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def send_owner_alert(self, *, title: str, body: str):
        self.calls.append((title, body))
        return {"sent": 1}


class _EmptyDiscovery:
    async def discover_immunefi_targets(self, **_kwargs):
        return []

    async def discover_all_supported_networks(self, **_kwargs):
        return []


def _autopilot() -> tuple[ScoutAutopilot, _StubNotifier]:
    notifier = _StubNotifier()
    autopilot = ScoutAutopilot(audit_service=AuditService(), discovery_service=_EmptyDiscovery())
    autopilot._notifications = notifier
    return autopilot, notifier


async def _running_dummy(autopilot: ScoutAutopilot) -> asyncio.Task:
    """Mark the autopilot 'running' with an inert task that does not heartbeat,
    so health/stall logic can be exercised deterministically."""
    task = asyncio.create_task(asyncio.sleep(30))
    autopilot._task = task
    autopilot._stop_event = asyncio.Event()
    autopilot._manual_enabled = True
    return task


@pytest.mark.asyncio
async def test_healthy_false_when_not_running():
    autopilot, _ = _autopilot()
    assert autopilot.is_running is False
    assert autopilot.healthy is False
    assert autopilot.status().healthy is False


@pytest.mark.asyncio
async def test_healthy_reflects_heartbeat_and_failure_streak():
    autopilot, _ = _autopilot()
    task = await _running_dummy(autopilot)
    try:
        autopilot._heartbeat()
        assert autopilot.healthy is True

        # Stale heartbeat -> unhealthy.
        autopilot._last_heartbeat_at = utc_now() - timedelta(hours=6)
        assert autopilot.healthy is False

        # Fresh heartbeat but a long failure streak -> unhealthy.
        autopilot._heartbeat()
        autopilot._consecutive_failures = autopilot._settings.scout_max_consecutive_failures
        assert autopilot.healthy is False
    finally:
        task.cancel()


@pytest.mark.asyncio
async def test_watchdog_restarts_dead_loop_and_alerts():
    autopilot, notifier = _autopilot()
    # Simulate a loop that died: a completed task while we should be running.
    dead = asyncio.create_task(asyncio.sleep(0))
    await dead
    autopilot._task = dead
    autopilot._manual_enabled = True
    assert autopilot.is_running is False

    await autopilot._watchdog_tick()
    try:
        assert autopilot.is_running is True  # loop brought back
        assert autopilot._restart_count == 1
        assert len(notifier.calls) == 1
        assert "auto-restarted" in notifier.calls[0][1]
    finally:
        await autopilot.stop()


@pytest.mark.asyncio
async def test_watchdog_alerts_on_stall_once_then_dedupes():
    autopilot, notifier = _autopilot()
    task = await _running_dummy(autopilot)
    try:
        autopilot._last_heartbeat_at = utc_now() - timedelta(hours=6)  # stalled
        assert autopilot.healthy is False

        await autopilot._watchdog_tick()
        assert len(notifier.calls) == 1  # paged once

        await autopilot._watchdog_tick()
        assert len(notifier.calls) == 1  # deduped while still stalled

        # A clean cycle clears the latch so a future stall can alert again.
        autopilot._stall_alerted = False
        autopilot._heartbeat()
        assert autopilot.healthy is True
    finally:
        task.cancel()


@pytest.mark.asyncio
async def test_watchdog_does_not_restart_after_manual_stop():
    autopilot, _ = _autopilot()
    await autopilot.start()
    assert autopilot.is_running is True
    await autopilot.stop()
    assert autopilot.is_running is False
    # Watchdog tick after a manual stop must not resurrect the loop.
    await autopilot._watchdog_tick()
    assert autopilot.is_running is False


@pytest.mark.asyncio
async def test_start_sets_heartbeat_health_and_watchdog():
    autopilot, _ = _autopilot()
    try:
        status = await autopilot.start()
        assert status.running is True
        assert status.healthy is True
        assert autopilot._last_heartbeat_at is not None
        assert autopilot._watchdog_task is not None and not autopilot._watchdog_task.done()
    finally:
        await autopilot.stop()
        assert autopilot._watchdog_task is None
