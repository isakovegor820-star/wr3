import httpx
import pytest
from fastapi.testclient import TestClient

from wr3_api.core.config import Settings
from wr3_api.main import create_app
from wr3_api.services.news import NewsIngestionService, normalize_defillama_hack


def test_normalize_defillama_hack_public_record():
    item = normalize_defillama_hack(
        {
            "date": 1711065600,
            "name": "Example Bridge",
            "classification": "Access Control",
            "technique": "Private key compromise",
            "amount": 2_000_000,
            "chain": ["Ethereum"],
        }
    )

    assert item.source == "defillama-hacks"
    assert item.severity == "high"
    assert item.chain == "ethereum"
    assert item.category == "key_compromise"


@pytest.mark.asyncio
async def test_fetch_defillama_hacks_uses_no_key(monkeypatch):
    async def fake_get(self, url):
        assert url == "https://example.test/hacks"
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json=[
                {
                    "date": 1711065600,
                    "name": "Example Exploit",
                    "classification": "Protocol Logic",
                    "technique": "Infinite mint",
                    "amount": 4_800_000,
                    "chain": ["Base"],
                }
            ],
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    payload = await NewsIngestionService(Settings(defillama_hacks_url="https://example.test/hacks")).fetch_defillama_hacks(limit=1)

    assert payload["free_no_key"] is True
    assert payload["count"] == 1
    assert payload["items"][0]["title"] == "Example Exploit"


def test_news_hacks_endpoint_is_available():
    client = TestClient(create_app())

    response = client.get("/v1/news/hacks?limit=1")

    assert response.status_code in {200, 502}
