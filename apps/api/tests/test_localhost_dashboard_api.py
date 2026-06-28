from fastapi.testclient import TestClient

from wr3_api.main import create_app


client = TestClient(create_app())


def test_local_dashboard_lists_audits_with_filters():
    response = client.post(
        "/v1/audits",
        json={
            "chain": "base",
            "address": "0x00000000000000000000000000000000000000da",
            "source": "contract DashboardCase { function auth(address a) public { require(tx.origin == a); } }",
            "tier": "hobby",
        },
    )
    assert response.status_code == 200
    audit_id = response.json()["audit_id"]

    # Anonymous local-dashboard call lists audits but must NOT leak owner tokens.
    listed = client.get("/v1/audits", params={"chain": "base", "severity": "high"})
    assert listed.status_code == 200
    rows = listed.json()
    row = next(item for item in rows if item["audit_id"] == audit_id)
    assert row["chain"] == "base"
    assert row["owner_access_token"] is None  # owner token is reviewer-only, never leaked to anon
    assert row["finding_count"] >= 1
    assert row["highest_severity"] == "high"
    assert row["project_key"].startswith("base:")

    # An authenticated reviewer does receive the owner token (needed to open the owner view).
    as_reviewer = client.get(
        "/v1/audits", params={"chain": "base", "severity": "high"}, headers={"X-WR3-Reviewer": "true"}
    )
    assert as_reviewer.status_code == 200
    reviewer_row = next(item for item in as_reviewer.json() if item["audit_id"] == audit_id)
    assert reviewer_row["owner_access_token"]


def test_disclosure_case_list_is_reviewer_only():
    created = client.post(
        "/v1/disclosure-cases",
        headers={"X-WR3-Reviewer": "true"},
        json={
            "finding_id": "wr3-find-dashboard-list",
            "project_contact": "security@example.com",
            "scope_note": "Passive disclosure only",
        },
    )
    assert created.status_code == 200
    case_id = created.json()["id"]

    forbidden = client.get("/v1/disclosure-cases")
    assert forbidden.status_code == 403

    listed = client.get("/v1/disclosure-cases", headers={"X-WR3-Reviewer": "true"})
    assert listed.status_code == 200
    assert any(item["id"] == case_id for item in listed.json())
