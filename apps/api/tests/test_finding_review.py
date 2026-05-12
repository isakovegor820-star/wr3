from fastapi.testclient import TestClient

from wr3_api.main import create_app


client = TestClient(create_app())


def test_reviewer_can_mark_finding_review_status():
    created = client.post(
        "/v1/audits",
        json={
            "chain": "base",
            "address": "0x0000000000000000000000000000000000000000",
            "source": "contract Vault { function auth(address a) public { require(tx.origin == a); } }",
        },
    )
    assert created.status_code == 200
    payload = created.json()
    findings = client.get(
        f"/v1/audits/{payload['audit_id']}/findings",
        params={"owner_token": payload["owner_access_token"]},
    ).json()
    finding_id = findings[0]["id"]

    forbidden = client.post(
        f"/v1/audits/{payload['audit_id']}/findings/{finding_id}/review",
        json={"status": "approved", "note": "reviewed"},
    )
    assert forbidden.status_code == 403

    reviewed = client.post(
        f"/v1/audits/{payload['audit_id']}/findings/{finding_id}/review",
        headers={"X-WR3-Reviewer": "true"},
        json={"status": "approved", "note": "reviewed"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["human_review_status"] == "approved"

    events = client.get(
        f"/v1/audits/{payload['audit_id']}/events",
        params={"owner_token": payload["owner_access_token"]},
    )
    assert any(event["event_type"] == "finding_reviewed" for event in events.json())
