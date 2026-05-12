from fastapi.testclient import TestClient

from wr3_api.main import create_app


client = TestClient(create_app())


def test_billing_plans_are_public_and_match_mvp_tiers():
    response = client.get("/v1/billing/plans")

    assert response.status_code == 200
    tiers = {item["tier"] for item in response.json()}
    assert tiers == {"free", "hobby", "team", "pro"}


def test_one_shot_packages_are_public_and_disclaimer_safe():
    response = client.get("/v1/billing/one-shot-packages")

    assert response.status_code == 200
    packages = response.json()
    assert {package["id"] for package in packages} == {
        "pre_launch_quickcheck",
        "poc_report",
        "deep_ai_assisted_audit",
    }
    assert any("No active mainnet actions" in limitation for limitation in packages[0]["limitations"])


def test_manual_usdc_intent_requires_authenticated_user():
    forbidden = client.post("/v1/billing/manual-usdc-intents", json={"tier": "team"})
    assert forbidden.status_code == 403

    response = client.post(
        "/v1/billing/manual-usdc-intents",
        headers={"X-WR3-User": "payer"},
        json={"tier": "team"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tier"] == "team"
    assert payload["amount_usd"] == 99
    assert "manual_usdc_confirmation_required" in payload["limitations"]


def test_checkout_intent_requires_auth_and_provider_configuration(monkeypatch):
    monkeypatch.delenv("WR3_POLAR_CHECKOUT_BASE_URL", raising=False)
    response = client.post("/v1/billing/checkout-intents", json={"tier": "hobby", "provider": "polar"})
    assert response.status_code == 403

    configured = client.post(
        "/v1/billing/checkout-intents",
        headers={"X-WR3-User": "payer"},
        json={"tier": "hobby", "provider": "polar"},
    )

    assert configured.status_code == 200
    payload = configured.json()
    assert payload["provider"] == "polar"
    assert payload["status"] == "requires_provider_configuration"
    assert "polar_checkout_url_not_configured" in payload["limitations"]


def test_manual_subscription_confirmation_is_reviewer_only():
    forbidden = client.post(
        "/v1/billing/subscriptions/confirm-manual",
        headers={"X-WR3-User": "payer"},
        json={
            "user_id": "dev:payer",
            "tier": "team",
            "provider": "manual_usdc",
            "tx_reference": "base:0xabc",
        },
    )
    assert forbidden.status_code == 403

    confirmed = client.post(
        "/v1/billing/subscriptions/confirm-manual",
        headers={"X-WR3-Reviewer": "true"},
        json={
            "user_id": "dev:payer",
            "tier": "team",
            "provider": "manual_usdc",
            "tx_reference": "base:0xabc",
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "active"

    subscription = client.get("/v1/billing/subscription", headers={"X-WR3-User": "payer"})
    assert subscription.status_code == 200
    assert subscription.json()["tier"] == "team"
