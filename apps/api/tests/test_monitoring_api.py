from fastapi.testclient import TestClient

from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import ScoutTarget
from wr3_api.main import create_app
from wr3_api.services import target_discovery


client = TestClient(create_app())


async def fake_discover(*args, **kwargs):
    return [
        ScoutTarget(
            protocol_name="Local Protocol",
            slug="local-protocol",
            category="Testing",
            chain=Chain.BASE,
            address="0x4444444444444444444444444444444444444444",
            tvl_usd=12345,
            official_url="https://example.org",
            security_txt_url="https://example.org/.well-known/security.txt",
            security_email_guess="security@example.org",
            limitations=["fixture_target"],
        )
    ]


def test_monitoring_targets_endpoint(monkeypatch):
    monkeypatch.setattr(target_discovery.TargetDiscoveryService, "discover_defillama_protocols", fake_discover)

    response = client.get("/v1/monitoring/targets", params={"limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["protocol_name"] == "Local Protocol"
    assert body[0]["chain"] == "base"
    assert body[0]["security_email_guess"] == "security@example.org"


def test_scout_run_once_dry_run(monkeypatch):
    monkeypatch.setattr(target_discovery.TargetDiscoveryService, "discover_defillama_protocols", fake_discover)

    response = client.post(
        "/v1/monitoring/scout/run-once",
        json={"limit": 1, "dry_run": True, "chains": ["base"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["discovered_count"] == 1
    assert body["queued_count"] == 0
    assert body["skipped_count"] == 1
    assert "no_auto_support_messages" in body["limitations"]


def test_scout_run_once_queues_passive_audit(monkeypatch):
    monkeypatch.setattr(target_discovery.TargetDiscoveryService, "discover_defillama_protocols", fake_discover)

    response = client.post(
        "/v1/monitoring/scout/run-once",
        json={"limit": 1, "dry_run": False, "chains": ["base"], "requested_depth": "preliminary"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["queued_count"] == 1
    queued = body["audits"][0]
    assert queued["chain"] == "base"
    assert queued["address"] == "0x4444444444444444444444444444444444444444"
    assert queued["owner_access_token"]
    status = client.get(queued["status_url"], params={"owner_token": queued["owner_access_token"]})
    assert status.status_code == 200


def test_scout_run_all_queues_supported_network_cycle(monkeypatch):
    async def fake_all(*args, **kwargs):
        return [
            ScoutTarget(
                protocol_name="Base Protocol",
                slug="base-protocol",
                category="Testing",
                chain=Chain.BASE,
                address="0x5555555555555555555555555555555555555555",
            ),
            ScoutTarget(
                protocol_name="Ethereum Protocol",
                slug="ethereum-protocol",
                category="Testing",
                chain=Chain.ETHEREUM,
                address="0x6666666666666666666666666666666666666666",
            ),
        ]

    monkeypatch.setattr(target_discovery.TargetDiscoveryService, "discover_all_supported_networks", fake_all)

    response = client.post(
        "/v1/monitoring/scout/run-all",
        json={"per_chain_limit": 1, "dry_run": False, "requested_depth": "deep", "tier": "team"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["discovered_count"] == 2
    assert body["queued_count"] == 2
    assert "all_supported_networks_cycle" in body["limitations"]


def test_review_queue_buckets_audits(monkeypatch):
    monkeypatch.setattr(target_discovery.TargetDiscoveryService, "discover_defillama_protocols", fake_discover)
    created = client.post(
        "/v1/monitoring/scout/run-once",
        json={"limit": 1, "dry_run": False, "chains": ["base"], "requested_depth": "preliminary"},
    )
    assert created.status_code == 200

    response = client.get("/v1/monitoring/review-queue")

    assert response.status_code == 200
    body = response.json()
    assert body["totals"]["total"] >= 1
    assert set(body["totals"]).issuperset({"ready_to_write", "needs_validation", "skip", "total"})
