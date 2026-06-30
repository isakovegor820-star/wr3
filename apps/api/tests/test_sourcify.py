"""Tests for the keyless Sourcify source puller."""
import httpx
import pytest

from wr3_api.domain.enums import Chain
from wr3_api.services.explorers import SourcifySourcePuller, default_explorer_pullers


@pytest.mark.asyncio
async def test_sourcify_returns_verified_source():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/v2/contract/1/" in request.url.path  # ethereum chainId
        return httpx.Response(
            200,
            json={"sources": {"Token.sol": {"content": "contract Token { uint x; }"}}, "match": "match"},
            request=request,
        )

    puller = SourcifySourcePuller(transport=httpx.MockTransport(handler))
    result = await puller.pull(chain=Chain.ETHEREUM, address="0x" + "1" * 40)

    assert result.status == "verified"
    assert "contract Token" in (result.source or "")
    assert result.contract_name == "Token"


@pytest.mark.asyncio
async def test_sourcify_404_is_missing_not_crash():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"}, request=request)

    puller = SourcifySourcePuller(transport=httpx.MockTransport(handler))
    result = await puller.pull(chain=Chain.ETHEREUM, address="0x" + "2" * 40)

    assert result.status == "missing"  # graceful, not an exception


def test_sourcify_is_first_keyless_puller():
    names = [p.name for p in default_explorer_pullers()]
    assert names[0] == "sourcify"  # keyless source tried before the key-gated explorers
