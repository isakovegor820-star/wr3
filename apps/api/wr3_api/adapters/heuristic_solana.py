from __future__ import annotations

from wr3_api.adapters.base import EngineAdapter, EngineRunOptions, EngineRunResult, NormalizedSource, Timer
from wr3_api.domain.enums import Chain, Exploitability, HumanReviewStatus, Severity
from wr3_api.domain.schemas import ContractRef, Evidence, Finding, SourceLocation, Taxonomy


class HeuristicSolanaAdapter(EngineAdapter):
    name = "wr3_heuristic_solana"

    async def version(self) -> str:
        return "wr3-heuristic-solana-v0.1"

    def supports(self, source: NormalizedSource) -> bool:
        return source.chain == Chain.SOLANA

    async def run(self, source: NormalizedSource, options: EngineRunOptions) -> EngineRunResult:
        with Timer() as timer:
            findings = self._scan(source, options.audit_id)
        return EngineRunResult(
            engine=self.name,
            status="success",
            findings=findings,
            raw_output=f"solana_heuristic_findings={len(findings)}",
            duration_ms=timer.duration_ms,
        )

    def _scan(self, source: NormalizedSource, audit_id: str) -> list[Finding]:
        lower_source = source.source.lower()
        findings: list[Finding] = []

        if "uncheckedaccount" in lower_source or "accountinfo<" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Unchecked Solana account requires owner and signer validation",
                    category="solana_account_validation",
                    severity=Severity.MEDIUM,
                    confidence=0.66,
                    exploitability=Exploitability.UNKNOWN,
                    trace="UncheckedAccount or AccountInfo usage detected",
                    impact="Unvalidated accounts can let callers substitute attacker-controlled accounts.",
                    recommendation="Validate owner, signer, mutability, and expected PDA seeds for every unchecked account.",
                )
            )

        if (
            ("authority:" in lower_source or "admin:" in lower_source or "owner:" in lower_source)
            and "accountinfo<" in lower_source
            and "signer<" not in lower_source
        ):
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Authority account is not typed as a Signer",
                    category="solana_signer",
                    severity=Severity.MEDIUM,
                    confidence=0.68,
                    exploitability=Exploitability.UNKNOWN,
                    trace="authority/admin/owner AccountInfo detected without a Signer typed constraint",
                    impact="A missing signer constraint can let callers route privileged instructions through an arbitrary account.",
                    recommendation="Use Signer<'info> for authorities or explicitly check is_signer before privileged actions.",
                )
            )

        if (
            ("#[account(mut)]" in lower_source or "accountinfo<" in lower_source)
            and "seeds" not in lower_source
            and ("config:" in lower_source or "vault:" in lower_source or "pda" in lower_source)
        ):
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="PDA-like account lacks explicit seed constraints",
                    category="solana_pda",
                    severity=Severity.LOW,
                    confidence=0.54,
                    exploitability=Exploitability.THEORETICAL,
                    trace="mutable config/vault/PDA-like account detected without obvious seeds constraint",
                    impact="Missing seed or owner checks can allow account substitution in Anchor programs.",
                    recommendation="Add #[account(seeds = [...], bump)] or equivalent owner/address constraints.",
                )
            )

        if "init_if_needed" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="init_if_needed can enable account reinitialization footguns",
                    category="solana_accounting",
                    severity=Severity.MEDIUM,
                    confidence=0.62,
                    exploitability=Exploitability.THEORETICAL,
                    trace="init_if_needed constraint detected",
                    impact="Reinitialization mistakes can reset state or bypass intended one-time setup.",
                    recommendation="Add explicit initialization state checks and document why init_if_needed is required.",
                )
            )

        if "invoke_signed" in lower_source and "seeds" not in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Signed CPI path needs explicit PDA seed review",
                    category="solana_pda",
                    severity=Severity.LOW,
                    confidence=0.45,
                    exploitability=Exploitability.UNKNOWN,
                    trace="invoke_signed detected without obvious seed constraints in source slice",
                    impact="Incorrect PDA seed validation can authorize unintended program actions.",
                    recommendation="Ensure PDA seeds, bumps, and account constraints are explicit and tested.",
                )
            )

        if not findings:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="No Solana heuristic findings detected",
                    category="informational",
                    severity=Severity.INFO,
                    confidence=0.82,
                    exploitability=Exploitability.UNKNOWN,
                    trace="Solana heuristic scan completed",
                    impact="This does not mean the program is safe; Solana beta coverage is intentionally limited.",
                    recommendation="Run Anchor tests, Trident fuzzing, and human review before deployment.",
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
