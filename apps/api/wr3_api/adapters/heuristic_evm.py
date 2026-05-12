from __future__ import annotations

import re

from wr3_api.adapters.base import EngineAdapter, EngineRunOptions, EngineRunResult, NormalizedSource, Timer
from wr3_api.domain.enums import Chain, Exploitability, HumanReviewStatus, Severity
from wr3_api.domain.schemas import ContractRef, Evidence, Finding, SourceLocation, Taxonomy


class HeuristicEvmAdapter(EngineAdapter):
    name = "wr3_heuristic_evm"

    async def version(self) -> str:
        return "wr3-heuristic-evm-v0.1"

    def supports(self, source: NormalizedSource) -> bool:
        return source.chain in {Chain.ETHEREUM, Chain.BASE, Chain.BSC, Chain.ARBITRUM}

    async def run(self, source: NormalizedSource, options: EngineRunOptions) -> EngineRunResult:
        with Timer() as timer:
            findings = self._scan(source, options.audit_id)
        return EngineRunResult(
            engine=self.name,
            status="success",
            findings=findings,
            raw_output=f"heuristic_findings={len(findings)}",
            duration_ms=timer.duration_ms,
        )

    def _scan(self, source: NormalizedSource, audit_id: str) -> list[Finding]:
        lower_source = source.source.lower()
        findings: list[Finding] = []

        if "tx.origin" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Authorization depends on tx.origin",
                    category="access_control",
                    severity=Severity.HIGH,
                    confidence=0.82,
                    exploitability=Exploitability.LIKELY,
                    trace="tx.origin usage detected",
                    impact="Phishing flows can pass authorization through an intermediate caller.",
                    recommendation="Use msg.sender based authorization and explicit role checks.",
                )
            )

        if "delegatecall" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Delegatecall requires strict target control",
                    category="upgradeability",
                    severity=Severity.HIGH,
                    confidence=0.72,
                    exploitability=Exploitability.THEORETICAL,
                    trace="delegatecall usage detected",
                    impact="A controlled or unvalidated delegatecall target can modify caller storage.",
                    recommendation="Restrict delegatecall targets and validate implementation code hashes.",
                )
            )

        if re.search(r"\.call\s*(\{|\.value)", lower_source):
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Low-level value transfer needs reentrancy review",
                    category="reentrancy",
                    severity=Severity.MEDIUM,
                    confidence=0.68,
                    exploitability=Exploitability.UNKNOWN,
                    trace="low-level call with value pattern detected",
                    impact="External calls before state updates can enable reentrant accounting bugs.",
                    recommendation="Use checks-effects-interactions and a reentrancy guard where appropriate.",
                )
            )

        if "selfdestruct" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Selfdestruct path is present",
                    category="lifecycle",
                    severity=Severity.MEDIUM,
                    confidence=0.75,
                    exploitability=Exploitability.THEORETICAL,
                    trace="selfdestruct usage detected",
                    impact="Contract lifecycle controls may permanently remove code or alter assumptions.",
                    recommendation="Remove selfdestruct unless it is explicitly required and access-controlled.",
                )
            )

        privileged_function = re.search(r"function\s+(mint|burn|sweep|withdraw|set[a-z0-9_]*)\s*\(", lower_source)
        has_common_guard = any(
            guard in lower_source
            for guard in ["onlyowner", "onlyrole", "requiresauth", "auth", "msg.sender ==", "_checkowner"]
        )
        if privileged_function and not has_common_guard:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Privileged-looking function lacks an obvious access guard",
                    category="access_control",
                    severity=Severity.MEDIUM,
                    confidence=0.58,
                    exploitability=Exploitability.THEORETICAL,
                    trace=f"{privileged_function.group(1)} function detected without common owner/role guard tokens",
                    impact="An unrestricted privileged function can let arbitrary callers mint, sweep, or change critical configuration.",
                    recommendation="Add explicit role checks, owner checks, or document why the function is intentionally permissionless.",
                )
            )

        if "onlyowner" in lower_source and re.search(r"\bmint\s*\(", lower_source):
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Owner-controlled mint path affects token centralization",
                    category="centralization",
                    severity=Severity.LOW,
                    confidence=0.76,
                    exploitability=Exploitability.UNKNOWN,
                    trace="onlyOwner mint function pattern detected",
                    impact="A privileged owner may be able to change supply assumptions.",
                    recommendation="Document mint limits, use multisig ownership, or add immutable caps.",
                )
            )

        if not findings:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="No heuristic findings detected",
                    category="informational",
                    severity=Severity.INFO,
                    confidence=0.9,
                    exploitability=Exploitability.UNKNOWN,
                    trace="heuristic scan completed",
                    impact="This does not mean the contract is safe; only that this MVP pass found no known pattern.",
                    recommendation="Run full static analysis, LLM triage, and human review before launch.",
                )
            )

        return findings

    def _finding(
        self,
        source: NormalizedSource,
        audit_id: str,
        *,
        summary: str,
        category: str,
        severity: Severity,
        confidence: float,
        exploitability: Exploitability,
        trace: str,
        impact: str,
        recommendation: str,
    ) -> Finding:
        return Finding(
            audit_id=audit_id,
            chain=source.chain,
            contract=ContractRef(
                address=source.address,
                name=source.contract_name,
                file=source.file_name,
            ),
            location=SourceLocation(file=source.file_name),
            taxonomy=Taxonomy(swc=None, cwe=None, wr3_category=category),
            severity=severity,
            confidence=confidence,
            exploitability=exploitability,
            sources=[self.name],
            evidence=Evidence(static_trace=trace),
            summary=summary,
            description=trace,
            impact=impact,
            recommendation=recommendation,
            human_review_status=(
                HumanReviewStatus.PENDING
                if severity in {Severity.CRITICAL, Severity.HIGH}
                else HumanReviewStatus.NOT_REQUIRED
            ),
        )
