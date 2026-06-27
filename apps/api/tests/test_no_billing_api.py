from fastapi.testclient import TestClient

from wr3_api.main import create_app


client = TestClient(create_app())


def test_billing_routes_are_not_exposed():
    assert client.get("/v1/billing/plans").status_code == 404
    assert client.get("/v1/billing/one-shot-packages").status_code == 404
    assert client.get("/v1/billing/subscription", headers={"X-WR3-User": "payer"}).status_code == 404

