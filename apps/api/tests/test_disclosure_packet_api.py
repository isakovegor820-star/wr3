from uuid import UUID

from fastapi.testclient import TestClient

from wr3_api.api.routes.audits import service
from wr3_api.core.config import get_settings
from wr3_api.domain.enums import AuditState, Chain, Exploitability, PocStatus, Severity
from wr3_api.domain.schemas import ContractRef, Evidence, Finding, SourceLocation, Taxonomy
from wr3_api.main import create_app


client = TestClient(create_app())
LOCAL_TELEGRAM_HEADERS = {"X-WR3-Local-Emulator": "true"}


def _confirmed_record():
    created = client.post(
        "/v1/audits",
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000000",
            "source": "contract Vault { function withdraw() external {} }",
            "requested_depth": "deep",
            "visibility": "private",
            "user_intent": "monitoring",
        },
    )
    assert created.status_code == 200
    record = service.get_record(UUID(created.json()["audit_id"]))
    finding = Finding(
        audit_id=str(record.audit_id),
        chain=Chain.BASE,
        contract=ContractRef(address=record.request.address, name="Vault", file="src/Vault.sol"),
        location=SourceLocation(file="src/Vault.sol", start_line=42, function="withdraw"),
        taxonomy=Taxonomy(wr3_category="reentrancy"),
        severity=Severity.HIGH,
        confidence=0.92,
        exploitability=Exploitability.CONFIRMED,
        sources=["foundry_poc"],
        evidence=Evidence(
            poc_status=PocStatus.CONFIRMED,
            poc_artifact_uri="artifact://private/poc-result",
            static_trace="private fork/test trace stored for reviewers",
        ),
        summary="External call before state update",
        description="Candidate reentrancy path confirmed in isolated fork/test.",
        impact="A user balance accounting path may be abused in an isolated reproduction, creating material protocol risk.",
        recommendation="Update state before external calls and add a reentrancy guard.",
    )
    finding.disclosure_assessment = service._finding_disclosure_assessment(
        finding,
        ai_fallback=False,
        failed_engines=[],
        source_is_verified=True,
    )
    record.findings = [finding]
    record.state = AuditState.COMPLETED
    service.save_record(record)
    return record, finding


def test_confirmed_poc_and_official_contact_prepares_needs_human_approval_packet():
    record, finding = _confirmed_record()

    response = client.post(
        "/v1/disclosure-cases/prepare",
        headers={"X-WR3-Reviewer": "true"},
        json={
            "audit_id": str(record.audit_id),
            "finding_id": finding.id,
            "project_name": "Vault Protocol",
            "official_contact": "https://example.com/.well-known/security.txt",
            "contact_source": "security_txt",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["readiness_state"] == "needs_human_approval"
    assert body["confirmed_by_poc"] is True
    assert body["pdfs_generated"] is True
    assert body["approved_to_contact"] is False
    assert body["needs_human_approval"] is True
    case = client.get(f"/v1/disclosure-cases/{body['case_id']}", headers={"X-WR3-Reviewer": "true"}).json()
    assert any("[draft]: safe draft generated" in item for item in case["contact_log"])


def test_approve_and_manual_sent_are_reviewer_only_and_append_contact_log():
    record, finding = _confirmed_record()
    packet = client.post(
        "/v1/disclosure-cases/prepare",
        headers={"X-WR3-Reviewer": "true"},
        json={
            "audit_id": str(record.audit_id),
            "finding_id": finding.id,
            "official_contact": "security@example.org",
            "contact_source": "official_website_email",
        },
    ).json()
    case_id = packet["case_id"]

    assert client.post(f"/v1/disclosure-cases/{case_id}/approve", json={}).status_code == 403
    assert client.post(f"/v1/disclosure-cases/{case_id}/manual-sent", json={}).status_code == 403

    approved = client.post(
        f"/v1/disclosure-cases/{case_id}/approve",
        headers={"X-WR3-Reviewer": "true"},
        json={"note": "human approved"},
    )
    assert approved.status_code == 200
    assert approved.json()["readiness_state"] == "approved_to_contact"
    assert approved.json()["approved_to_contact"] is True

    sent = client.post(
        f"/v1/disclosure-cases/{case_id}/manual-sent",
        headers={"X-WR3-Reviewer": "true"},
        json={"channel": "manual_email", "note": "operator sent via mailbox"},
    )
    assert sent.status_code == 200
    assert sent.json()["readiness_state"] == "manually_sent"

    case = client.get(f"/v1/disclosure-cases/{case_id}", headers={"X-WR3-Reviewer": "true"}).json()
    assert any("manual send logged" in item for item in case["contact_log"])


def test_external_pdf_omits_forbidden_wording_and_transaction_recipe():
    record, finding = _confirmed_record()
    case_id = client.post(
        "/v1/disclosure-cases/prepare",
        headers={"X-WR3-Reviewer": "true"},
        json={
            "audit_id": str(record.audit_id),
            "finding_id": finding.id,
            "official_contact": "https://immunefi.com/bounty/example",
            "contact_source": "bug_bounty_portal",
        },
    ).json()["case_id"]

    response = client.get(f"/v1/disclosure-cases/{case_id}/reports/external.pdf", headers={"X-WR3-Reviewer": "true"})

    assert response.status_code == 200
    body = response.content.decode("latin-1", errors="ignore").lower()
    assert "scam" not in body
    assert "fraud" not in body
    assert "working poc" not in body
    assert "exploit recipe" not in body
    assert "exploit steps" not in body
    assert "mainnet exploit steps" not in body


def test_telegram_normal_mode_filters_yellow_and_ops_mode_reports_operational_alerts():
    record, finding = _confirmed_record()
    ready_case = client.post(
        "/v1/disclosure-cases/prepare",
        headers={"X-WR3-Reviewer": "true"},
        json={
            "audit_id": str(record.audit_id),
            "finding_id": finding.id,
            "official_contact": "security@example.org",
            "contact_source": "official_website_email",
        },
    ).json()["case_id"]
    yellow_record, yellow_finding = _confirmed_record()
    yellow_case = client.post(
        "/v1/disclosure-cases/prepare",
        headers={"X-WR3-Reviewer": "true"},
        json={
            "audit_id": str(yellow_record.audit_id),
            "finding_id": yellow_finding.id,
            "official_contact": "https://t.me/project",
            "contact_source": "telegram",
        },
    ).json()["case_id"]

    normal = client.get("/v1/telegram/disclosure-alerts?mode=normal", headers={"X-WR3-Reviewer": "true"})
    assert normal.status_code == 200
    normal_cases = {item["case_id"] for item in normal.json()["alerts"]}
    assert ready_case in normal_cases
    assert yellow_case not in normal_cases
    assert all(item["auto_sends_external_message"] is False for item in normal.json()["alerts"])

    ops = client.get("/v1/telegram/disclosure-alerts?mode=ops", headers={"X-WR3-Reviewer": "true"})
    assert ops.status_code == 200
    yellow_alert = next(item for item in ops.json()["alerts"] if item.get("case_id") == yellow_case)
    assert yellow_alert["kind"] == "ops_context"
    assert "не готов" in yellow_alert["text"]
    assert "почти готово" not in yellow_alert["text"]
    assert any(item["kind"] == "ops" for item in ops.json()["alerts"])


def test_telegram_disclosure_callbacks_require_reviewer_allowlist_and_log_manual_send(monkeypatch):
    record, finding = _confirmed_record()
    case_id = client.post(
        "/v1/disclosure-cases/prepare",
        headers={"X-WR3-Reviewer": "true"},
        json={
            "audit_id": str(record.audit_id),
            "finding_id": finding.id,
            "official_contact": "https://example.com/.well-known/security.txt",
            "contact_source": "security_txt",
        },
    ).json()["case_id"]

    blocked = client.post(
        "/v1/telegram/webhook",
        headers=LOCAL_TELEGRAM_HEADERS,
        json={"callback_query": {"data": f"wr3:approve:{case_id}", "from": {"id": 999}}},
    )
    assert blocked.status_code == 403

    monkeypatch.setattr(get_settings(), "telegram_reviewer_user_ids", ["1508"])
    approved = client.post(
        "/v1/telegram/webhook",
        headers=LOCAL_TELEGRAM_HEADERS,
        json={"callback_query": {"data": f"wr3:approve:{case_id}", "from": {"id": 1508}}},
    )
    assert approved.status_code == 200
    approved_body = approved.json()
    assert approved_body["packet"]["readiness_state"] == "approved_to_contact"
    assert approved_body["telegram_alert"]["kind"] == "approved_to_contact"
    assert approved_body["auto_sends_external_message"] is False

    sent = client.post(
        "/v1/telegram/webhook",
        headers=LOCAL_TELEGRAM_HEADERS,
        json={"callback_query": {"data": f"wr3:sent:{case_id}", "from": {"id": 1508}}},
    )
    assert sent.status_code == 200
    assert sent.json()["packet"]["readiness_state"] == "manually_sent"
    assert sent.json()["auto_sends_external_message"] is False

    case = client.get(f"/v1/disclosure-cases/{case_id}", headers={"X-WR3-Reviewer": "true"}).json()
    assert any("manual send logged" in item for item in case["contact_log"])
