from __future__ import annotations

import shutil
import time
from dataclasses import dataclass

from wr3_api.core.config import get_settings
from wr3_api.domain.schemas import AuditEvent, AuditRecord, EngineRunSummary, Finding
from wr3_api.services.artifacts import ArtifactEncryptionRequired, ArtifactVault
from wr3_api.services.sandbox import SandboxPolicy


@dataclass(frozen=True)
class FuzzWorkerResult:
    status: str
    duration_ms: int
    finding_count: int
    engines_considered: tuple[str, ...]
    artifact_uri: str | None = None
    error: str | None = None


class FuzzingWorker:
    name = "ai_fuzzing"
    _commands: dict[str, tuple[str, ...]] = {
        "medusa": ("medusa", "fuzz"),
        "ityfuzz": ("ityfuzz", "evm"),
    }

    def __init__(self, sandbox_policy: SandboxPolicy | None = None) -> None:
        settings = get_settings()
        self._sandbox_policy = sandbox_policy or SandboxPolicy(
            allowed_rpc_hosts=settings.sandbox_allowed_rpc_hosts,
            timeout_seconds=settings.sandbox_default_timeout_seconds,
        )
        self._artifact_vault = ArtifactVault()

    def should_consider(self, record: AuditRecord) -> bool:
        return record.request.requested_depth == "deep"

    async def run(self, record: AuditRecord, findings: list[Finding]) -> FuzzWorkerResult:
        started = time.perf_counter()
        for engine, argv in self._commands.items():
            decision = self._sandbox_policy.validate_argv(argv)
            if not decision.allowed:
                return self._skipped(started, findings, decision.reason, considered=(engine,))

        available = tuple(engine for engine in self._commands if shutil.which(engine))
        if not available:
            return self._skipped(
                started,
                findings,
                "fuzzing_binaries_missing",
                considered=tuple(self._commands),
            )
        return self._skipped(
            started,
            findings,
            "fuzzing_generation_stub_requires_invariant_sandbox",
            considered=available,
        )

    def record_result(self, record: AuditRecord, result: FuzzWorkerResult) -> None:
        if result.error:
            record.limitations.append(result.error)
        artifact_uri = result.artifact_uri or self._store_status_artifact(record, result)
        record.engine_runs.append(
            EngineRunSummary(
                audit_id=record.audit_id,
                engine=self.name,
                status=result.status,
                duration_ms=result.duration_ms,
                artifact_uri=artifact_uri,
                error=result.error,
            )
        )
        record.events.append(
            AuditEvent(
                audit_id=record.audit_id,
                event_type="fuzzing_worker_result",
                payload={
                    "worker": self.name,
                    "status": result.status,
                    "finding_count": result.finding_count,
                    "engines_considered": list(result.engines_considered),
                    "artifact_private": artifact_uri is not None,
                    "artifact_uri": artifact_uri,
                    "error": result.error,
                },
            )
        )

    def _store_status_artifact(self, record: AuditRecord, result: FuzzWorkerResult) -> str | None:
        try:
            artifact = self._artifact_vault.store_json(
                audit_id=str(record.audit_id),
                kind="fuzzer_counterexample",
                payload={
                    "worker": self.name,
                    "status": result.status,
                    "reason": result.error,
                    "finding_count": result.finding_count,
                    "engines_considered": list(result.engines_considered),
                    "counterexample_analysis": "not_available_in_skipped_or_stubbed_localhost_run",
                    "mode": "localhost_safe_status_artifact",
                },
                private=True,
            )
            return artifact.uri
        except ArtifactEncryptionRequired:
            record.limitations.append("fuzzing_status_artifact_requires_encryption")
            return None

    def _skipped(
        self,
        started: float,
        findings: list[Finding],
        reason: str,
        *,
        considered: tuple[str, ...] = (),
    ) -> FuzzWorkerResult:
        return FuzzWorkerResult(
            status="skipped",
            duration_ms=int((time.perf_counter() - started) * 1000),
            finding_count=len(findings),
            engines_considered=considered,
            error=reason,
        )
