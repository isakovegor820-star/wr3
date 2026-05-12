from fastapi.testclient import TestClient

from wr3_api.main import create_app


client = TestClient(create_app())


def test_ready_endpoint_reports_component_posture_without_secrets():
    response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert "checks" in payload
    assert "database_url" not in str(payload).lower()


def test_live_endpoint_is_minimal_liveness_probe():
    response = client.get("/live")

    assert response.status_code == 200
    assert response.json()["status"] == "live"
