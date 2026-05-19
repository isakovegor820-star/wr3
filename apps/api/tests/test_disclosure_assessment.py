from pathlib import Path

from wr3_api.adapters.source_tree import materialize_source_tree
from wr3_api.domain.enums import Chain, Exploitability, PocStatus, Severity
from wr3_api.domain.schemas import ContractRef, Evidence, Finding, SourceLocation, Taxonomy
from wr3_api.services.audit_service import AuditService


def make_finding(
    *,
    sources: list[str],
    severity: Severity = Severity.HIGH,
    confidence: float = 0.82,
    exploitability: Exploitability = Exploitability.LIKELY,
    poc_status: PocStatus = PocStatus.NOT_ATTEMPTED,
    location: SourceLocation | None = None,
) -> Finding:
    return Finding(
        audit_id="audit-test",
        chain=Chain.BASE,
        contract=ContractRef(
            address="0x0000000000000000000000000000000000000000",
            name="Vault",
            file="src/Vault.sol",
        ),
        location=location or SourceLocation(),
        taxonomy=Taxonomy(wr3_category="reentrancy"),
        severity=severity,
        confidence=confidence,
        exploitability=exploitability,
        sources=sources,
        evidence=Evidence(poc_status=poc_status),
        summary="External call before state update",
        description="Candidate reentrancy path.",
        impact="Funds may be withdrawn twice if the path is real.",
        recommendation="Update state before external calls and add a reentrancy guard.",
    )


def test_heuristic_only_missing_location_is_too_early_to_contact_support():
    service = AuditService()
    assessment = service._finding_disclosure_assessment(
        make_finding(sources=["wr3_heuristic_evm"], confidence=0.90),
        ai_fallback=True,
        failed_engines=["aderyn", "slither"],
        source_is_verified=True,
    )

    assert assessment.verdict == "too_early"
    assert assessment.can_contact_support is False
    assert assessment.false_positive_risk == "high"
    assert "Точное место не определено" == assessment.location_label
    assert any("heuristic detector" in gap for gap in assessment.evidence_gaps)
    assert any("ИИ-триаж" in gap for gap in assessment.evidence_gaps)


def test_confirmed_poc_is_ready_for_private_disclosure():
    service = AuditService()
    assessment = service._finding_disclosure_assessment(
        make_finding(
            sources=["foundry_poc"],
            exploitability=Exploitability.CONFIRMED,
            poc_status=PocStatus.CONFIRMED,
            location=SourceLocation(file="src/Vault.sol", start_line=42, function="withdraw"),
        ),
        ai_fallback=True,
        failed_engines=[],
        source_is_verified=True,
    )

    assert assessment.verdict == "can_write"
    assert assessment.verdict_label == "Можно писать"
    assert assessment.can_contact_support is True
    assert assessment.false_positive_risk == "low"
    assert "src/Vault.sol:42" in assessment.location_label


def test_strong_static_and_ai_signal_is_ready_without_poc_but_medium_fp_risk():
    service = AuditService()
    assessment = service._finding_disclosure_assessment(
        make_finding(
            sources=["wake"],
            confidence=0.78,
            exploitability=Exploitability.LIKELY,
            location=SourceLocation(file="contracts/Vault.sol", start_line=11, function="withdraw"),
        ),
        ai_fallback=False,
        failed_engines=[],
        source_is_verified=True,
    )

    assert assessment.verdict == "can_write"
    assert assessment.can_contact_support is True
    assert assessment.false_positive_risk == "medium"
    assert any("PoC" in gap for gap in assessment.evidence_gaps)


def test_materialize_source_tree_restores_explorer_multifile_layout(tmp_path: Path):
    source = """// file: src/B.sol
contract B {}
// file: src/A.sol
import "./B.sol";
contract A is B {}
"""

    tree = materialize_source_tree(tmp_path, source)

    assert tree.multi_file is True
    assert (tmp_path / "src" / "A.sol").read_text(encoding="utf-8").startswith("import")
    assert (tmp_path / "src" / "B.sol").read_text(encoding="utf-8").startswith("contract B")
