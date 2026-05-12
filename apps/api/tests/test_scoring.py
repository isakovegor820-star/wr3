from wr3_api.domain.enums import Chain, Exploitability, Severity
from wr3_api.domain.schemas import ContractRef, Finding, Taxonomy
from wr3_api.domain.scoring import score_audit


def make_finding(**overrides):
    payload = {
        "audit_id": "audit-test",
        "chain": Chain.BASE,
        "contract": ContractRef(address="0x0000000000000000000000000000000000000000", name="Vault"),
        "taxonomy": Taxonomy(swc=None, cwe=None, wr3_category="access_control"),
        "severity": Severity.HIGH,
        "confidence": 1,
        "exploitability": Exploitability.CONFIRMED,
        "sources": ["test"],
        "summary": "Owner bypass",
        "description": "Test",
        "impact": "Funds can be affected",
        "recommendation": "Add authorization",
    }
    payload.update(overrides)
    return Finding(**payload)


def test_confirmed_high_caps_score():
    score = score_audit([make_finding()])
    assert score.final_score == 69
    assert "confirmed_high" in score.caps_applied


def test_confirmed_critical_caps_score():
    score = score_audit([make_finding(severity=Severity.CRITICAL)])
    assert score.final_score == 39
    assert "confirmed_critical" in score.caps_applied


def test_dismissed_finding_is_not_penalized():
    score = score_audit([make_finding(exploitability=Exploitability.DISMISSED)])
    assert score.code_security_score == 100
