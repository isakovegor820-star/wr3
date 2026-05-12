from wr3_api.domain.enums import Chain, Exploitability, HumanReviewStatus, Severity
from wr3_api.domain.schemas import ContractRef, Finding, Taxonomy
from wr3_api.services.triage_agents import TriageConsensus


def make_finding(**overrides):
    data = {
        "audit_id": "audit",
        "chain": Chain.BASE,
        "contract": ContractRef(address="0x0000000000000000000000000000000000000000", name="Vault"),
        "taxonomy": Taxonomy(wr3_category="access_control"),
        "severity": Severity.MEDIUM,
        "confidence": 0.72,
        "exploitability": Exploitability.LIKELY,
        "sources": ["fixture"],
        "summary": "Access-control issue",
        "description": "Access-control issue",
        "impact": "Unauthorized action may be possible.",
        "recommendation": "Use explicit roles.",
    }
    data.update(overrides)
    return Finding(**data)


def test_triage_consensus_runs_four_agents_per_finding_and_escalates_logic_risk():
    result = TriageConsensus().run([make_finding()])

    assert len(result.verdicts) == 4
    assert result.findings[0].severity == Severity.HIGH
    assert result.findings[0].human_review_status == HumanReviewStatus.PENDING
    assert result.summary["agent_counts"]["severity_classifier"] == 1


def test_triage_consensus_dismisses_low_confidence_non_info_signal():
    result = TriageConsensus().run([make_finding(confidence=0.2, severity=Severity.LOW)])

    assert result.findings[0].exploitability == Exploitability.DISMISSED
    assert result.findings[0].dismissal_reason == "multi_agent_consensus_low_confidence"
