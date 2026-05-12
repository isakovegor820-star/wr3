from __future__ import annotations

from dataclasses import dataclass

from wr3_api.domain.enums import Exploitability, HumanReviewStatus, Severity
from wr3_api.domain.schemas import Finding


@dataclass(frozen=True)
class TriageVerdict:
    agent: str
    finding_id: str
    action: str
    reason: str
    severity: Severity | None = None
    confidence_delta: float = 0.0


@dataclass(frozen=True)
class TriageConsensusResult:
    findings: list[Finding]
    verdicts: list[TriageVerdict]

    @property
    def summary(self) -> dict[str, object]:
        action_counts: dict[str, int] = {}
        agent_counts: dict[str, int] = {}
        for verdict in self.verdicts:
            action_counts[verdict.action] = action_counts.get(verdict.action, 0) + 1
            agent_counts[verdict.agent] = agent_counts.get(verdict.agent, 0) + 1
        return {
            "agent_counts": agent_counts,
            "action_counts": action_counts,
            "finding_count": len(self.findings),
        }


class TriageConsensus:
    agents = (
        "severity_classifier",
        "false_positive_filter",
        "business_logic_reasoner",
        "cross_contract_analyzer",
    )

    def run(self, findings: list[Finding]) -> TriageConsensusResult:
        verdicts: list[TriageVerdict] = []
        for finding in findings:
            verdicts.extend(
                [
                    self._severity_classifier(finding),
                    self._false_positive_filter(finding),
                    self._business_logic_reasoner(finding),
                    self._cross_contract_analyzer(finding),
                ]
            )
        return TriageConsensusResult(
            findings=[self._apply_consensus(finding, verdicts) for finding in findings],
            verdicts=verdicts,
        )

    def _severity_classifier(self, finding: Finding) -> TriageVerdict:
        if finding.severity in {Severity.CRITICAL, Severity.HIGH}:
            return TriageVerdict(
                agent="severity_classifier",
                finding_id=finding.id,
                action="keep",
                reason="already_high_risk",
                severity=finding.severity,
                confidence_delta=0.02,
            )
        if finding.taxonomy.wr3_category in {"access_control", "oracle", "accounting"} and finding.confidence >= 0.65:
            return TriageVerdict(
                agent="severity_classifier",
                finding_id=finding.id,
                action="escalate",
                reason="logic_category_high_confidence",
                severity=Severity.HIGH if finding.severity == Severity.MEDIUM else finding.severity,
                confidence_delta=0.04,
            )
        return TriageVerdict(
            agent="severity_classifier",
            finding_id=finding.id,
            action="keep",
            reason="severity_reasonable_for_mvp_signal",
        )

    def _false_positive_filter(self, finding: Finding) -> TriageVerdict:
        if finding.confidence < 0.3 and finding.severity != Severity.INFO:
            return TriageVerdict(
                agent="false_positive_filter",
                finding_id=finding.id,
                action="dismiss",
                reason="confidence_below_threshold",
                confidence_delta=-0.1,
            )
        if finding.severity == Severity.INFO:
            return TriageVerdict(
                agent="false_positive_filter",
                finding_id=finding.id,
                action="keep_info",
                reason="informational_finding_not_security_claim",
            )
        return TriageVerdict(
            agent="false_positive_filter",
            finding_id=finding.id,
            action="keep",
            reason="sufficient_confidence",
        )

    def _business_logic_reasoner(self, finding: Finding) -> TriageVerdict:
        if finding.taxonomy.wr3_category in {"access_control", "oracle", "accounting", "liquidity"}:
            return TriageVerdict(
                agent="business_logic_reasoner",
                finding_id=finding.id,
                action="needs_context",
                reason="business_logic_category_requires_owner_review",
                confidence_delta=0.02,
            )
        if finding.taxonomy.wr3_category.startswith("solana_"):
            return TriageVerdict(
                agent="business_logic_reasoner",
                finding_id=finding.id,
                action="keep_beta",
                reason="solana_beta_signal_kept_with_limited_coverage",
            )
        return TriageVerdict(
            agent="business_logic_reasoner",
            finding_id=finding.id,
            action="keep",
            reason="pattern_level_signal",
        )

    def _cross_contract_analyzer(self, finding: Finding) -> TriageVerdict:
        if finding.taxonomy.wr3_category in {"upgradeability", "centralization"}:
            return TriageVerdict(
                agent="cross_contract_analyzer",
                finding_id=finding.id,
                action="needs_proxy_context",
                reason="cross_contract_or_owner_context_required",
                confidence_delta=0.01,
            )
        return TriageVerdict(
            agent="cross_contract_analyzer",
            finding_id=finding.id,
            action="not_applicable",
            reason="single_contract_signal",
        )

    def _apply_consensus(self, finding: Finding, verdicts: list[TriageVerdict]) -> Finding:
        related = [verdict for verdict in verdicts if verdict.finding_id == finding.id]
        actions = {verdict.action for verdict in related}
        updates: dict[str, object] = {}
        confidence = min(1.0, max(0.0, finding.confidence + sum(v.confidence_delta for v in related)))
        updates["confidence"] = confidence

        if "dismiss" in actions:
            updates["exploitability"] = Exploitability.DISMISSED
            updates["dismissal_reason"] = "multi_agent_consensus_low_confidence"
        else:
            escalations = [verdict.severity for verdict in related if verdict.action == "escalate" and verdict.severity]
            if escalations and finding.severity not in {Severity.CRITICAL, Severity.HIGH}:
                updates["severity"] = escalations[0]
                updates["human_review_status"] = HumanReviewStatus.PENDING
            elif finding.severity in {Severity.CRITICAL, Severity.HIGH}:
                updates["human_review_status"] = HumanReviewStatus.PENDING

        return finding.model_copy(update=updates)
