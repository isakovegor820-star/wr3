from fastapi.testclient import TestClient

from wr3_api.core.config import Settings
from wr3_api.main import create_app
from wr3_api.services.integrations import IntegrationStatusService


def test_integration_status_includes_p0_and_free_fallbacks():
    payload = IntegrationStatusService(
        Settings(
            etherscan_api_key="key",
            telegram_bot_token="secret-value",
            public_rpc_fallback_enabled=True,
        )
    ).summary()

    by_id = {item["id"]: item for item in payload["integrations"]}
    assert by_id["etherscan_v2"]["status"] == "configured"
    assert by_id["rpc"]["status"] == "free_fallback"
    assert by_id["telegram"]["status"] == "configured"
    assert by_id["solodit"]["status"] == "blocked"
    assert "secret-value" not in str(payload)


def test_integration_status_endpoint_is_public_and_sanitized():
    client = TestClient(create_app())

    response = client.get("/v1/integrations/status")

    assert response.status_code == 200
    payload = response.json()
    assert "integrations" in payload
    assert "rpc" in payload
    assert "WR3_ETHERSCAN_API_KEY" in payload["integrations"][0]["env_vars"]
