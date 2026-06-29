from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from wr3_api.core.config import Settings, get_settings
from wr3_api.domain.enums import AuditState, UserIntent, Visibility
from wr3_api.domain.schemas import (
    CreateAuditRequest,
    ScoutAutopilotRunRequest,
    ScoutAutopilotStatus,
    ScoutQueuedAudit,
    ScoutRunResult,
    ScoutTarget,
    utc_now,
)
from wr3_api.services.audit_service import AuditService
from wr3_api.services.auth import AuthContext
from wr3_api.services.dispatcher import dispatch_audit_processing_detached
from wr3_api.services.notifications import NotificationService
from wr3_api.services.target_discovery import TargetDiscoveryService


def _merge_targets(primary: list[ScoutTarget], secondary: list[ScoutTarget]) -> list[ScoutTarget]:
    """Merge two target lists, primary first, de-duplicated by (chain, address)."""
    merged: list[ScoutTarget] = []
    seen: set[tuple[object, str]] = set()
    for target in [*primary, *secondary]:
        key = (target.chain, target.address.lower())
        if key in seen:
            continue
        seen.add(key)
        merged.append(target)
    return merged


class ScoutAutopilot:
    def __init__(
        self,
        *,
        audit_service: AuditService,
        discovery_service: TargetDiscoveryService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._audit_service = audit_service
        self._discovery = discovery_service or TargetDiscoveryService(self._settings)
        self._notifications = NotificationService()
        self._task: asyncio.Task[None] | None = None
        self._watchdog_task: asyncio.Task[None] | None = None
        self._watchdog_stop: asyncio.Event | None = None
        self._processing_tasks: set[asyncio.Task[None]] = set()
        self._stop_event: asyncio.Event | None = None
        self._run_lock = asyncio.Lock()
        self._cycle_count = 0
        self._queued_total = 0
        self._immunefi_offset = 0
        self._defillama_offset = 0
        self._inflight: set = set()  # audit_ids currently scheduled for processing
        self._drained_total = 0
        self._restart_count = 0
        self._consecutive_failures = 0
        self._stall_alerted = False
        self._manual_enabled = False
        self._last_run_at = None
        self._next_run_at = None
        self._last_heartbeat_at: datetime | None = None
        self._last_error: str | None = None
        self._last_result: ScoutRunResult | None = None

    def _heartbeat(self) -> None:
        self._last_heartbeat_at = utc_now()

    @property
    def healthy(self) -> bool:
        """A running loop that has emitted a recent heartbeat and isn't stuck in a
        failure streak. Used by the watchdog and surfaced for external monitors."""
        if not self.is_running:
            return False
        if self._last_heartbeat_at is None:
            return True  # just started, first cycle not finished yet
        interval = max(self._settings.scout_default_interval_seconds, 60)
        threshold = interval * max(self._settings.scout_heartbeat_stall_factor, 1) + 120
        age = (utc_now() - self._last_heartbeat_at).total_seconds()
        if age > threshold:
            return False
        return self._consecutive_failures < max(self._settings.scout_max_consecutive_failures, 1)

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> ScoutAutopilotStatus:
        return ScoutAutopilotStatus(
            enabled=self._settings.scout_autopilot_enabled or self._manual_enabled,
            running=self.is_running,
            interval_seconds=self._settings.scout_default_interval_seconds,
            per_chain_limit=self._settings.scout_autopilot_per_chain_limit,
            min_tvl_usd=self._settings.scout_autopilot_min_tvl_usd,
            dedupe_window_hours=self._settings.scout_autopilot_dedupe_window_hours,
            process_queued=self._settings.scout_autopilot_process_queued,
            cycle_count=self._cycle_count,
            queued_total=self._queued_total,
            drained_total=self._drained_total,
            last_run_at=self._last_run_at,
            next_run_at=self._next_run_at,
            last_heartbeat_at=self._last_heartbeat_at,
            healthy=self.healthy,
            consecutive_failures=self._consecutive_failures,
            restart_count=self._restart_count,
            last_error=self._last_error,
            last_result=self._last_result,
            limitations=[
                "autopilot_passive_analysis_only",
                "autopilot_no_mainnet_broadcast",
                "autopilot_no_auto_support_messages",
                "autopilot_dedupes_recent_chain_address_targets",
                "autopilot_watchdog_restarts_dead_loop_and_alerts_on_stall",
            ],
        )

    async def start(self) -> ScoutAutopilotStatus:
        if self.is_running:
            self._start_watchdog()
            return self.status()
        self._manual_enabled = True
        self._stall_alerted = False
        self._stop_event = asyncio.Event()
        self._heartbeat()
        self._task = asyncio.create_task(self._loop(), name="wr3-scout-autopilot")
        self._start_watchdog()
        return self.status()

    async def stop(self) -> ScoutAutopilotStatus:
        # Tear the watchdog down first so it cannot resurrect the loop we are stopping.
        if self._watchdog_stop is not None:
            self._watchdog_stop.set()
        watchdog = self._watchdog_task
        if watchdog is not None and not watchdog.done():
            watchdog.cancel()
            try:
                await watchdog
            except asyncio.CancelledError:
                pass
        self._watchdog_task = None
        if self._stop_event is not None:
            self._stop_event.set()
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._manual_enabled = False
        self._next_run_at = None
        return self.status()

    def _start_watchdog(self) -> None:
        if self._watchdog_task is not None and not self._watchdog_task.done():
            return
        self._watchdog_stop = asyncio.Event()
        self._watchdog_task = asyncio.create_task(self._watchdog(), name="wr3-scout-watchdog")

    async def _watchdog(self) -> None:
        """Supervise the scout loop: restart it if the task dies and page the owner
        when it stalls, so the platform keeps hunting 24/7 without a babysitter."""
        while self._watchdog_stop is not None and not self._watchdog_stop.is_set():
            try:
                await self._watchdog_tick()
            except Exception:  # pragma: no cover - watchdog must never die
                pass
            interval = max(self._settings.scout_watchdog_interval_seconds, 1)
            for _ in range(interval):
                if self._watchdog_stop is None or self._watchdog_stop.is_set():
                    return
                await asyncio.sleep(1)

    async def _watchdog_tick(self) -> None:
        should_run = self._manual_enabled or self._settings.scout_autopilot_enabled
        if not should_run:
            return
        if not self.is_running:
            # The loop task died unexpectedly — bring it back.
            self._restart_count += 1
            self._stop_event = asyncio.Event()
            self._heartbeat()
            self._task = asyncio.create_task(self._loop(), name="wr3-scout-autopilot")
            await self._alert_stall(f"scout loop was not running — auto-restarted (#{self._restart_count})")
            return
        if not self.healthy:
            await self._alert_stall("scout loop is stalled (heartbeat stale or repeated cycle failures)")

    async def _alert_stall(self, reason: str) -> None:
        if self._stall_alerted:
            return
        self._stall_alerted = True
        try:
            await self._notifications.send_owner_alert(
                title="wr3 scout autopilot unhealthy",
                body=(
                    f"{reason}. cycles={self._cycle_count} "
                    f"consecutive_failures={self._consecutive_failures} last_error={self._last_error}"
                ),
            )
        except Exception:  # pragma: no cover - alerting is best-effort
            pass

    async def run_now(self, request: ScoutAutopilotRunRequest | None = None) -> ScoutRunResult:
        return await self._run_cycle(request or self._default_request())

    async def _loop(self) -> None:
        request = self._default_request()
        while self._stop_event is not None and not self._stop_event.is_set():
            self._heartbeat()
            await self._run_cycle(request)
            delay = max(self._settings.scout_default_interval_seconds, 60)
            self._next_run_at = utc_now() + timedelta(seconds=delay)
            for _ in range(delay):
                if self._stop_event.is_set():
                    return
                self._heartbeat()
                await asyncio.sleep(1)

    def _default_request(self) -> ScoutAutopilotRunRequest:
        return ScoutAutopilotRunRequest(
            per_chain_limit=self._settings.scout_autopilot_per_chain_limit,
            min_tvl_usd=self._settings.scout_autopilot_min_tvl_usd,
            dedupe_window_hours=self._settings.scout_autopilot_dedupe_window_hours,
            process_queued=self._settings.scout_autopilot_process_queued,
        )

    async def _run_cycle(self, request: ScoutAutopilotRunRequest) -> ScoutRunResult:
        async with self._run_lock:
            self._last_run_at = utc_now()
            self._last_error = None
            try:
                # Immunefi first: in-scope, paying bounty targets take priority over
                # broad DeFiLlama discovery and are fork-PoC eligible.
                bounty_targets = await self._discovery.discover_immunefi_targets(
                    limit=self._settings.immunefi_max_targets_per_cycle,
                    offset=self._immunefi_offset,
                    min_payout_usd=self._settings.immunefi_min_payout_usd,
                    chains=request.chains,
                )
                defillama_targets = await self._discovery.discover_all_supported_networks(
                    per_chain_limit=request.per_chain_limit,
                    offset=self._defillama_offset,
                    min_tvl_usd=request.min_tvl_usd,
                    chains=request.chains,
                )
                # Page deeper next cycle so the scout sweeps the WHOLE scope over
                # time instead of re-scanning the same top targets every cycle.
                self._immunefi_offset += self._settings.immunefi_max_targets_per_cycle
                self._defillama_offset += request.per_chain_limit
                targets = _merge_targets(bounty_targets, defillama_targets)
                audits, skipped_limitations = await self._queue_targets(targets, request)
                drained = await self._drain_standing_queue(request)
                result = ScoutRunResult(
                    source="immunefi+defillama_protocols" if bounty_targets else "defillama_protocols",
                    discovered_count=len(targets),
                    queued_count=len(audits),
                    skipped_count=len(targets) - len(audits),
                    drained_count=drained,
                    targets=targets,
                    audits=audits,
                    limitations=[
                        "autopilot_all_supported_networks_cycle",
                        f"immunefi_bounty_targets:{len(bounty_targets)}",
                        "free_sources_immunefi_and_defillama_no_api_key",
                        "passive_analysis_only",
                        "no_auto_support_messages",
                        "contacts_and_scope_require_manual_verification",
                        f"dedupe_window_hours:{request.dedupe_window_hours}",
                        f"standing_queue_drained:{drained}",
                        *skipped_limitations,
                    ],
                )
                self._cycle_count += 1
                self._queued_total += result.queued_count
                self._last_result = result
                self._consecutive_failures = 0
                self._stall_alerted = False  # a clean cycle clears any stall alert latch
                return result
            except Exception as exc:
                self._last_error = f"{exc.__class__.__name__}:{exc}"
                self._consecutive_failures += 1
                result = ScoutRunResult(
                    source="defillama_protocols",
                    discovered_count=0,
                    queued_count=0,
                    skipped_count=0,
                    targets=[],
                    audits=[],
                    limitations=["autopilot_cycle_failed", self._last_error],
                )
                self._last_result = result
                return result

    async def _queue_targets(
        self,
        targets: list[ScoutTarget],
        request: ScoutAutopilotRunRequest,
    ) -> tuple[list[ScoutQueuedAudit], list[str]]:
        audits: list[ScoutQueuedAudit] = []
        skipped_limitations: list[str] = []
        actor = AuthContext(
            user_id="wr3-scout-autopilot",
            provider="system",
            subject="scout-autopilot",
            is_reviewer=True,
        )
        for target in targets:
            existing = self._audit_service.find_recent_monitoring_audit(
                chain=target.chain,
                address=target.address,
                window_hours=request.dedupe_window_hours,
            )
            if existing is not None:
                skipped_limitations.append(
                    f"duplicate_recent_target_skipped:{target.chain}:{target.address}:{existing.audit_id}"
                )
                continue
            audit_request = CreateAuditRequest(
                chain=target.chain,
                address=target.address,
                source=None,
                allow_bytecode_only=True,
                requested_depth=request.requested_depth,
                visibility=Visibility.PRIVATE,
                user_intent=UserIntent.MONITORING,
                tier=request.tier,
                bounty=target.bounty,
            )
            record = await self._audit_service.create_audit(audit_request, actor)
            record.limitations.extend(
                [
                    f"autopilot_scout_target:{target.source}:{target.protocol_name}",
                    "autopilot_support_contact_must_be_verified_manually",
                    "autopilot_no_auto_disclosure",
                ]
            )
            if target.bounty is not None:
                record.limitations.append(
                    f"autopilot_immunefi_in_scope:{target.bounty.program}:"
                    f"max_payout_usd={int(target.bounty.max_payout_usd or 0)}"
                )
            self._audit_service.save_record(record)
            process_limitations: list[str] = []
            if record.state == AuditState.QUEUED and request.process_queued:
                process_limitations = ["autopilot_processing_scheduled"]
                self._schedule_processing(record.audit_id)
            audits.append(
                ScoutQueuedAudit(
                    audit_id=record.audit_id,
                    owner_access_token=record.owner_access_token,
                    chain=target.chain,
                    address=target.address,
                    protocol_name=target.protocol_name,
                    status_url=f"/v1/audits/{record.audit_id}",
                    report_url=f"/v1/audits/{record.audit_id}/report",
                    limitations=[*target.limitations, *record.limitations, *process_limitations],
                )
            )
        return audits, skipped_limitations

    def _schedule_processing(self, audit_id) -> None:
        # Route through the dispatcher: Celery (durable, survives an API restart)
        # when WR3_TASK_BACKEND=celery, otherwise an in-process asyncio task.
        self._inflight.add(audit_id)
        _limitations, task = dispatch_audit_processing_detached(
            audit_id=audit_id,
            local_processor=self._audit_service.process_audit,
        )
        if task is not None:
            self._processing_tasks.add(task)
            task.add_done_callback(self._processing_tasks.discard)
            task.add_done_callback(lambda _t, _id=audit_id: self._inflight.discard(_id))
        else:
            # Celery path: no local handle to await — clear the guard now; the worker
            # transitions the job out of QUEUED so a later drain won't re-pick it.
            self._inflight.discard(audit_id)

    async def _drain_standing_queue(self, request: ScoutAutopilotRunRequest) -> int:
        """Process audits left QUEUED by earlier cycles (or manual runs) so the
        standing queue never sits unprocessed — fresh-target processing only covers
        what the current cycle discovers."""
        limit = self._settings.scout_autopilot_drain_limit
        if limit <= 0 or not request.process_queued:
            return 0
        # Pull a few extra so ids already mid-flight don't eat into the budget.
        candidates = self._audit_service.list_queued_audit_ids(limit=limit + len(self._inflight))
        drained = 0
        for audit_id in candidates:
            if drained >= limit:
                break
            if audit_id in self._inflight:
                continue
            self._schedule_processing(audit_id)
            drained += 1
        self._drained_total += drained
        return drained
