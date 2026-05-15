from fastapi.testclient import TestClient

from wr3_api.main import create_app
from wr3_api.services.tools import ToolStatusService


def test_tool_status_service_reports_required_tools():
    payload = ToolStatusService().summary()

    assert payload["required_total"] >= 4
    assert "tools" in payload
    assert {tool["id"] for tool in payload["tools"]} >= {
        "foundry_forge",
        "slither",
        "aderyn",
        "wake",
    }


def test_tools_status_endpoint_is_stable_when_tools_missing():
    client = TestClient(create_app())

    response = client.get("/v1/tools/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "partial"}
    assert isinstance(payload["missing_required"], list)
