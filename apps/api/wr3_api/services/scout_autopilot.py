from __future__ import annotations

import asyncio
from datetime import timedelta

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
from wr3_api.services.target_discovery import TargetDiscoveryService


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
        self._task: asyncio.Task[None] | None = None
        self._processing_tasks: set[asyncio.Task[None]] = set()
        self._stop_event: asyncio.Event | None = None
        self._run_lock = asyncio.Lock()
        self._cycle_count = 0
        self._queued_total = 0
        self._manual_enabled = False
        self._last_run_at = None
        self._next_run_at = None
        self._last_error: str | None = None
        self._last_result: ScoutRunResult | None = None

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
            last_run_at=self._last_run_at,
            next_run_at=self._next_run_at,
            last_error=self._last_error,
            last_result=self._last_result,
            limitations=[
                "autopilot_passive_analysis_only",
                "autopilot_no_mainnet_broadcast",
                "autopilot_no_auto_support_messages",
                "autopilot_dedupes_recent_chain_address_targets",
            ],
        )

    async def start(self) -> ScoutAutopilotStatus:
        if self.is_running:
            return self.status()
        self._manual_enabled = True
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._loop(), name="wr3-scout-autopilot")
        return self.status()

    async def stop(self) -> ScoutAutopilotStatus:
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

    async def run_now(self, request: ScoutAutopilotRunRequest | None = None) -> ScoutRunResult:
        return await self._run_cycle(request or self._default_request())

    async def _loop(self) -> None:
        request = self._default_request()
        while self._stop_event is not None and not self._stop_event.is_set():
            await self._run_cycle(request)
            delay = max(self._settings.scout_default_interval_seconds, 60)
            self._next_run_at = utc_now() + timedelta(seconds=delay)
            for _ in range(delay):
                if self._stop_event.is_set():
                    return
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
                targets = await self._discovery.discover_all_supported_networks(
                    per_chain_limit=request.per_chain_limit,
                    min_tvl_usd=request.min_tvl_usd,
                    chains=request.chains,
                )
                audits, skipped_limitations = await self._queue_targets(targets, request)
                result = ScoutRunResult(
                    source="defillama_protocols",
                    discovered_count=len(targets),
                    queued_count=len(audits),
                    skipped_count=len(targets) - len(audits),
                    targets=targets,
                    audits=audits,
                    limitations=[
                        "autopilot_all_supported_networks_cycle",
                        "free_source_defillama_protocols_no_api_key",
                        "passive_analysis_only",
                        "no_auto_support_messages",
                        "contacts_and_scope_require_manual_verification",
                        f"dedupe_window_hours:{request.dedupe_window_hours}",
                        *skipped_limitations,
                    ],
                )
                self._cycle_count += 1
                self._queued_total += result.queued_count
                self._last_result = result
                return result
            except Exception as exc:
                self._last_error = f"{exc.__class__.__name__}:{exc}"
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
            )
            record = await self._audit_service.create_audit(audit_request, actor)
            record.limitations.extend(
                [
                    f"autopilot_scout_target:{target.source}:{target.protocol_name}",
                    "autopilot_support_contact_must_be_verified_manually",
                    "autopilot_no_auto_disclosure",
                ]
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
        _limitations, task = dispatch_audit_processing_detached(
            audit_id=audit_id,
            local_processor=self._audit_service.process_audit,
        )
        if task is not None:
            self._processing_tasks.add(task)
            task.add_done_callback(self._processing_tasks.discard)
