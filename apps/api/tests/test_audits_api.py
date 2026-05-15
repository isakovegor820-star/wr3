from fastapi.testclient import TestClient

from wr3_api.main import create_app


client = TestClient(create_app())


def wait_for_audit(audit_id: str, owner_token: str, expected_state: str = "completed"):
    status = None
    for _ in range(5):
        status = client.get(f"/v1/audits/{audit_id}", params={"owner_token": owner_token})
        assert status.status_code == 200
        if status.json()["state"] == expected_state:
            return status
    assert status is not None
    assert status.json()["state"] == expected_state
    return status


def test_create_audit_with_source_completes_report():
    response = client.post(
        "/v1/audits",
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000000",
            "source": "contract Vault { function auth(address a) public { require(tx.origin == a); } }",
            "requested_depth": "preliminary",
            "visibility": "private",
            "user_intent": "pre_launch_self_check",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "queued"
    assert payload["owner_access_token"]

    audit_id = payload["audit_id"]
    owner_token = payload["owner_access_token"]
    status = wait_for_audit(audit_id, owner_token)
    assert status.json()["score"]["final_score"] <= 100
    assert status.json()["access"]["is_owner"] is True

    unauth_findings = client.get(f"/v1/audits/{audit_id}/findings")
    assert unauth_findings.status_code == 403

    public_findings = client.get(f"/v1/audits/{audit_id}/findings", params={"public": True})
    assert public_findings.status_code == 200

    findings = client.get(f"/v1/audits/{audit_id}/findings", params={"owner_token": owner_token})
    assert findings.status_code == 200
    assert any(item["taxonomy"]["wr3_category"] == "access_control" for item in findings.json())

    report = client.get(f"/v1/audits/{audit_id}/report", params={"owner_token": owner_token})
    assert report.status_code == 200
    assert "ИИ-предаудит" in report.text

    raw_outputs = client.get(f"/v1/audits/{audit_id}/raw-outputs", params={"owner_token": owner_token})
    assert raw_outputs.status_code == 200
    assert raw_outputs.json()["gated"] is True

    events = client.get(f"/v1/audits/{audit_id}/events", params={"owner_token": owner_token})
    assert events.status_code == 200
    assert any(item["event_type"] == "state_transition" for item in events.json())


def test_address_without_source_needs_source():
    response = client.post(
        "/v1/audits",
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000000",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    status = wait_for_audit(payload["audit_id"], payload["owner_access_token"], expected_state="needs_source")
    assert status.json()["state"] == "needs_source"


def test_address_without_verified_source_can_run_bytecode_only_limited_scan():
    response = client.post(
        "/v1/audits",
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000000",
            "allow_bytecode_only": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    status = wait_for_audit(payload["audit_id"], payload["owner_access_token"])
    body = status.json()

    assert body["state"] == "completed"
    assert body["source_metadata"]["bytecode_only"] is True
    assert body["score"]["final_score"] <= 79
    assert "bytecode_only_limited_scan" in body["limitations"]


def test_privileged_function_without_guard_is_flagged():
    response = client.post(
        "/v1/audits",
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000006",
            "source": "pragma solidity ^0.8.20; contract Token { function mint(address to, uint256 amount) external {} }",
            "requested_depth": "preliminary",
            "visibility": "private",
            "user_intent": "pre_launch_self_check",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    findings_response = client.get(
        f"/v1/audits/{payload['audit_id']}/findings",
        params={"owner_token": payload["owner_access_token"]},
    )
    categories = {finding["taxonomy"]["wr3_category"] for finding in findings_response.json()}

    assert "access_control" in categories


def test_disclosure_case_stub():
    response = client.post(
        "/v1/disclosure-cases",
        headers={"X-WR3-Reviewer": "true"},
        json={
            "finding_id": "wr3-find-test",
            "project_contact": "security@example.com",
            "scope_note": "Passive disclosure only",
        },
    )
    assert response.status_code == 200
    case = response.json()
    assert case["status"] == "private_contact_pending"

    read = client.get(f"/v1/disclosure-cases/{case['id']}", headers={"X-WR3-Reviewer": "true"})
    assert read.status_code == 200

    contact = client.post(
        f"/v1/disclosure-cases/{case['id']}/contact-log",
        headers={"X-WR3-Reviewer": "true"},
        json={"channel": "email", "message": "security@example.com contacted"},
    )
    assert contact.status_code == 200
    assert any("security@example.com contacted" in item for item in contact.json()["contact_log"])

    advanced = client.post(
        f"/v1/disclosure-cases/{case['id']}/advance",
        headers={"X-WR3-Reviewer": "true"},
        json={"status": "seal_911_escalation", "note": "No response after first window"},
    )
    assert advanced.status_code == 200
    assert advanced.json()["status"] == "seal_911_escalation"

    forbidden = client.get(f"/v1/disclosure-cases/{case['id']}")
    assert forbidden.status_code == 403


def test_private_audit_accepts_dev_header_owner():
    response = client.post(
        "/v1/audits",
        headers={"X-WR3-User": "local-owner"},
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000000",
            "source": "contract Vault { function f(address a) public { require(tx.origin == a); } }",
        },
    )
    assert response.status_code == 200
    audit_id = response.json()["audit_id"]

    wait_for_audit(audit_id, response.json()["owner_access_token"])
    status = client.get(f"/v1/audits/{audit_id}", headers={"X-WR3-User": "local-owner"})
    assert status.status_code == 200
    assert status.json()["access"]["auth_provider"] == "dev-header"

    other = client.get(f"/v1/audits/{audit_id}", headers={"X-WR3-User": "other-user"})
    assert other.status_code == 403


def test_auth_stubs_issue_sessions():
    nonce = client.post(
        "/v1/auth/siwe/nonce",
        json={"address": "0x0000000000000000000000000000000000000000", "chain": "ethereum"},
    )
    assert nonce.status_code == 200
    nonce_payload = nonce.json()

    verify = client.post(
        "/v1/auth/siwe/verify",
        json={
            "address": "0x0000000000000000000000000000000000000000",
            "nonce": nonce_payload["nonce"],
            "message": nonce_payload["message"],
            "signature": "0xstub-signature",
        },
    )
    assert verify.status_code == 200
    assert verify.json()["provider"] == "siwe"
    assert "siwe_signature_verification_disabled_local_stub" in verify.json()["limitations"]

    email = client.post("/v1/auth/email/request-link", json={"email": "dev@example.com"})
    assert email.status_code == 200
    assert email.json()["provider"] == "email"

    requested_link = client.post("/v1/auth/email/magic-link", json={"email": "dev@example.com"})
    assert requested_link.status_code == 200
    link_payload = requested_link.json()
    assert link_payload["delivery_enabled"] is False
    assert link_payload["dev_verify_token"]

    verified_link = client.post(
        "/v1/auth/email/verify-link",
        json={"email": "dev@example.com", "token": link_payload["dev_verify_token"]},
    )
    assert verified_link.status_code == 200
    assert verified_link.json()["provider"] == "email"
    assert "email_magic_link_verified" in verified_link.json()["limitations"]


def test_owner_can_delete_private_audit():
    response = client.post(
        "/v1/audits",
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000000",
            "source": "contract Plain { function ping() external pure returns (uint256) { return 1; } }",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    forbidden = client.delete(f"/v1/audits/{payload['audit_id']}")
    assert forbidden.status_code == 403

    deleted = client.delete(
        f"/v1/audits/{payload['audit_id']}",
        params={"owner_token": payload["owner_access_token"]},
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    missing = client.get(
        f"/v1/audits/{payload['audit_id']}",
        params={"owner_token": payload["owner_access_token"]},
    )
    assert missing.status_code == 404
