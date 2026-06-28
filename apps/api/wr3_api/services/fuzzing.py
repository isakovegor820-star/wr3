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
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import AuditEvent, AuditRecord, EngineRunSummary, Finding
from wr3_api.services.artifacts import ArtifactEncryptionRequired, ArtifactVault
from wr3_api.services.poc import ensure_solidity_pragma, extract_primary_contract
from wr3_api.services.sandbox import SandboxPolicy
from wr3_api.services.tool_paths import tool_subprocess_env


@dataclass(frozen=True)
class FuzzWorkerResult:
    status: str
    duration_ms: int
    finding_count: int
    engines_considered: tuple[str, ...]
    artifact_uri: str | None = None
    error: str | None = None
    violated_properties: tuple[str, ...] = ()
    counterexample: str | None = None


class FuzzingWorker:
    name = "ai_fuzzing"
    _commands: dict[str, tuple[str, ...]] = {
        "medusa": ("medusa", "fuzz"),
    }

    def __init__(self, sandbox_policy: SandboxPolicy | None = None) -> None:
        settings = get_settings()
        self._settings = settings
        self._sandbox_policy = sandbox_policy or SandboxPolicy(
            allowed_rpc_hosts=settings.sandbox_allowed_rpc_hosts,
            timeout_seconds=settings.sandbox_default_timeout_seconds,
        )
        self._artifact_vault = ArtifactVault()

    def should_consider(self, record: AuditRecord) -> bool:
        return record.request.requested_depth == "deep"

    async def run(self, record: AuditRecord, findings: list[Finding]) -> FuzzWorkerResult:
        started = time.perf_counter()
        if record.request.chain == Chain.SOLANA:
            return self._skipped(started, findings, "fuzzing_solana_uses_trident_not_medusa")

        for engine, argv in self._commands.items():
            decision = self._sandbox_policy.validate_argv(argv)
            if not decision.allowed:
                return self._skipped(started, findings, decision.reason, considered=(engine,))

        available = tuple(engine for engine in self._commands if shutil.which(engine))
        if not available:
            return self._skipped(
                started, findings, "fuzzing_binaries_missing", considered=tuple(self._commands)
            )

        source = record.request.source or ""
        if not source.strip():
            return self._skipped(started, findings, "fuzzing_requires_source", considered=available)

        source_with_pragma = ensure_solidity_pragma(source)
        target_name = extract_primary_contract(source_with_pragma)
        harness = build_invariant_harness(source_with_pragma, target_name)
        if harness is None:
            return self._skipped(
                started, findings, "fuzzing_no_supported_invariant_shape", considered=available
            )

        return await self._run_campaign(record, findings, started, source_with_pragma, harness, available)

    async def _run_campaign(
        self,
        record: AuditRecord,
        findings: list[Finding],
        started: float,
        source_with_pragma: str,
        harness: str,
        available: tuple[str, ...],
    ) -> FuzzWorkerResult:
        test_limit = self._settings.fuzz_test_limit
        timeout_s = self._settings.fuzz_timeout_seconds
        with tempfile.TemporaryDirectory(prefix="wr3-medusa-") as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "Target.sol").write_text(source_with_pragma, encoding="utf-8")
            (root / "src" / "Wr3Invariants.sol").write_text(harness, encoding="utf-8")
            (root / "foundry.toml").write_text("[profile.default]\nsrc='src'\ntest='test'\n", encoding="utf-8")
            (root / "medusa.json").write_text(
                json.dumps(build_medusa_config(test_limit, timeout_s), indent=1), encoding="utf-8"
            )

            try:
                proc = await asyncio.create_subprocess_exec(
                    "medusa",
                    "fuzz",
                    "--config",
                    "medusa.json",
                    cwd=root,
                    env=tool_subprocess_env(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError:
                return self._skipped(started, findings, "fuzzing_binaries_missing", considered=available)

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s + 30)
            except TimeoutError:
                proc.kill()
                return self._skipped(started, findings, "fuzzing_campaign_timeout", considered=available)

            output = stdout.decode(errors="replace") + "\n" + stderr.decode(errors="replace")
            parsed = parse_medusa_output(output, proc.returncode)

        status = parsed["status"]
        violated = tuple(parsed["violated_properties"])
        counterexample = parsed["counterexample"]
        artifact_uri, artifact_error = self._store_counterexample(
            record, status, parsed["reason"], violated, counterexample, available
        )

        error: str | None
        if status == "counterexample_found":
            error = None
        elif status == "no_violations":
            error = None
        else:
            error = parsed["reason"]
        return FuzzWorkerResult(
            status=status,
            duration_ms=int((time.perf_counter() - started) * 1000),
            finding_count=len(findings),
            engines_considered=available,
            artifact_uri=artifact_uri,
            error=artifact_error or error,
            violated_properties=violated,
            counterexample=counterexample,
        )

    def _store_counterexample(
        self,
        record: AuditRecord,
        status: str,
        reason: str | None,
        violated: tuple[str, ...],
        counterexample: str | None,
        available: tuple[str, ...],
    ) -> tuple[str | None, str | None]:
        try:
            artifact = self._artifact_vault.store_json(
                audit_id=str(record.audit_id),
                kind="fuzzer_counterexample",
                payload={
                    "worker": self.name,
                    "status": status,
                    "reason": reason,
                    "engine": "medusa",
                    "engines_considered": list(available),
                    "violated_properties": list(violated),
                    "counterexample": counterexample,
                    "mode": "medusa_invariant_campaign",
                },
                private=True,
            )
            return artifact.uri, None
        except ArtifactEncryptionRequired:
            record.limitations.append("fuzzing_status_artifact_requires_encryption")
            return None, None

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
                    "violated_properties": list(result.violated_properties),
                    "mode": "localhost_safe_status_artifact",
                },
                private=True,
            )
            return artifact.uri
        except ArtifactEncryptionRequired:
            record.limitations.append("fuzzing_status_artifact_requires_encryption")
            return None

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
                    "violated_properties": list(result.violated_properties),
                    "counterexample": (result.counterexample or "")[:2000] or None,
                    "artifact_private": artifact_uri is not None,
                    "artifact_uri": artifact_uri,
                    "error": result.error,
                },
            )
        )

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


def _public_address_mapping(source: str, name: str) -> bool:
    pattern = re.compile(
        r"mapping\s*\(\s*address\s*=>\s*uint(?:256)?\s*\)\s*public\s+" + re.escape(name) + r"\b"
    )
    return bool(pattern.search(source))


def _balance_accessor(source: str) -> str | None:
    for name in ("balances", "balanceOf"):
        if _public_address_mapping(source, name):
            return name
    return None


def build_invariant_harness(source: str, target_name: str | None) -> str | None:
    """Generate a Medusa invariant harness for a deposit/withdraw contract.

    Returns None when the target does not expose the shape we can soundly fuzz
    (a ``deposit``/``withdraw`` pair plus a public ``balances``/``balanceOf``
    accessor). The invariant is *solvency*: the contract must always hold at
    least the sum of the balances it still owes. A correct contract upholds this
    with equality; an accounting bug (e.g. a withdraw that fails to zero the
    balance) makes the recorded debt exceed the ETH on hand. Legitimate yield
    keeps balance >= debt, so this does not false-positive on interest-bearing
    vaults — we only flag genuine value loss, never normal accrual.
    """
    if not target_name:
        return None
    lowered = source.lower()
    if "function deposit" not in lowered or "function withdraw" not in lowered:
        return None
    accessor = _balance_accessor(source)
    if accessor is None:
        return None
    return f"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import "./Target.sol";

// wr3 Medusa invariant harness for {target_name}.
contract Wr3Actor {{
    {target_name} private target;

    constructor({target_name} _target) {{
        target = _target;
    }}

    function dep(uint256 amount) external {{
        target.deposit{{value: amount}}();
    }}

    receive() external payable {{}}
}}

contract Wr3Invariants {{
    {target_name} private target;
    Wr3Actor private victim;

    constructor() payable {{
        target = new {target_name}();
        victim = new Wr3Actor(target);
        // An honest depositor parks funds the harness must never be able to lose.
        payable(address(victim)).transfer(10 ether);
        victim.dep(10 ether);
    }}

    // Medusa drives these with fuzzed inputs / call ordering.
    function deposit(uint256 raw) public {{
        uint256 amount = raw % 5 ether;
        if (amount == 0 || address(this).balance < amount) {{
            return;
        }}
        target.deposit{{value: amount}}();
    }}

    function withdraw() public {{
        try target.withdraw() {{}} catch {{}}
    }}

    // INVARIANT: a solvent contract always holds at least what it still owes.
    function property_bank_solvent() public view returns (bool) {{
        uint256 owed = target.{accessor}(address(this)) + target.{accessor}(address(victim));
        return address(target).balance >= owed;
    }}

    receive() external payable {{}}
}}
"""


def build_medusa_config(test_limit: int, timeout_seconds: int) -> dict:
    return {
        "fuzzing": {
            "workers": 4,
            "timeout": timeout_seconds,
            "testLimit": test_limit,
            "callSequenceLength": 50,
            "corpusDirectory": "corpus",
            "targetContracts": ["Wr3Invariants"],
            "targetContractsBalances": [hex(100 * 10**18)],
            "deployerAddress": "0x30000",
            "senderAddresses": ["0x10000", "0x20000", "0x30000"],
            "testing": {
                "stopOnFailedTest": True,
                "stopOnNoTests": True,
                "testViewMethods": True,
                "assertionTesting": {"enabled": False},
                "propertyTesting": {"enabled": True, "testPrefixes": ["property_"]},
                "optimizationTesting": {"enabled": False},
            },
        },
        "compilation": {
            "platform": "crytic-compile",
            "platformConfig": {"target": ".", "solcVersion": "", "exportDirectory": "", "args": []},
        },
        "slither": {"useSlither": False},
        "logging": {"level": "info", "noColor": True},
    }


_SUMMARY_RE = re.compile(r"(\d+)\s+test\(s\)\s+passed,\s*(\d+)\s+test\(s\)\s+failed")
_FAILED_PROP_RE = re.compile(r"\[FAILED\]\s+Property Test:\s*(\S+)")


def parse_medusa_output(output: str, returncode: int | None) -> dict:
    """Map a Medusa campaign's output to a wr3 status.

    Medusa exits 0 when every property holds, 7 when a property is broken, and 6
    when no tests were discovered. We key off the parsed test-summary line first
    (most reliable) and fall back to the [FAILED] markers and the exit code.
    """
    violated = _FAILED_PROP_RE.findall(output)
    summary = _SUMMARY_RE.search(output)
    passed = failed = None
    if summary:
        passed, failed = int(summary.group(1)), int(summary.group(2))

    counterexample = _extract_counterexample(output)

    if (failed and failed > 0) or violated:
        return {
            "status": "counterexample_found",
            "violated_properties": violated or (["property_bank_solvent"] if failed else []),
            "counterexample": counterexample,
            "reason": "medusa_invariant_violated",
        }
    if (failed == 0 and passed is not None) or returncode == 0:
        return {
            "status": "no_violations",
            "violated_properties": [],
            "counterexample": None,
            "reason": "medusa_no_invariant_violation",
        }
    if "no assertion, property, optimization, or custom tests were found" in output:
        return {
            "status": "skipped",
            "violated_properties": [],
            "counterexample": None,
            "reason": "fuzzing_harness_exposed_no_invariants",
        }
    tail = output.strip()[-400:]
    return {
        "status": "skipped",
        "violated_properties": [],
        "counterexample": None,
        "reason": f"fuzzing_campaign_error:{tail}"[:500],
    }


def _extract_counterexample(output: str) -> str | None:
    marker = "failed after the following call sequence:"
    idx = output.find(marker)
    if idx == -1:
        return None
    start = idx + len(marker)
    end = output.find("[Property Test Execution Trace]", start)
    if end == -1:
        end = min(len(output), start + 2000)
    block = output[start:end].strip()
    return block[:2000] or None
