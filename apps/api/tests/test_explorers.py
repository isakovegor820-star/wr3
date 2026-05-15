import pytest
import httpx

from wr3_api.core.config import Settings
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import CreateAuditRequest
from wr3_api.services.audit_service import AuditService
from wr3_api.services.explorers import (
    EtherscanFamilySourcePuller,
    EtherscanV2SourcePuller,
    ExplorerSourceResult,
    ExplorerSourcePuller,
    _unwrap_explorer_source,
)


class MockExplorer(ExplorerSourcePuller):
    name = "mock_explorer"

    def supports(self, chain: Chain) -> bool:
        return chain == Chain.BASE

    async def pull(self, *, chain: Chain, address: str) -> ExplorerSourceResult:
        return ExplorerSourceResult(
            status="verified",
            source="contract Pulled { function auth(address a) public view { require(tx.origin == a); } }",
            contract_name="Pulled",
            file_name="Pulled.sol",
            explorer_url=f"mock:{chain}:{address}",
        )


@pytest.mark.asyncio
async def test_audit_service_pulls_verified_source_when_available():
    service = AuditService(explorers=[MockExplorer()])
    record = await service.create_audit(
        CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
        )
    )
    await service.process_audit(record.audit_id)
    record = service.get_record(record.audit_id)
    assert record.state == "completed"
    assert record.request.source is not None
    assert any(event.event_type == "source_pulled" for event in record.events)
    assert any(finding.taxonomy.wr3_category == "access_control" for finding in record.findings)


def test_unwrap_explorer_standard_json_sources():
    wrapped = (
        '{{"language":"Solidity","sources":{'
        '"src/B.sol":{"content":"contract B {}"},'
        '"src/A.sol":{"content":"contract A { function auth(address a) public { require(tx.origin == a); } }"}'
        '}}}'
    )

    source = _unwrap_explorer_source(wrapped)

    assert "// file: src/A.sol" in source
    assert "contract A" in source
    assert "contract B" in source


@pytest.mark.asyncio
async def test_etherscan_family_retries_transient_rate_limit():
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"message": "rate limit"})
        return httpx.Response(
            200,
            json={
                "status": "1",
                "message": "OK",
                "result": [
                    {
                        "SourceCode": "contract Pulled {}",
                        "ContractName": "Pulled",
                        "CompilerVersion": "v0.8.20+commit.test",
                        "Proxy": "0",
                    }
                ],
            },
        )

    settings = Settings(
        basescan_api_key="key",
        explorer_max_retries=1,
        explorer_retry_backoff_seconds=0,
    )
    puller = EtherscanFamilySourcePuller(settings=settings, transport=httpx.MockTransport(handler))

    result = await puller.pull(chain=Chain.BASE, address="0x0000000000000000000000000000000000000000")

    assert result.status == "verified"
    assert result.source == "contract Pulled {}"
    assert result.verified_at is not None
    assert result.metadata["CompilerVersion"] == "v0.8.20+commit.test"
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_etherscan_v2_uses_single_key_and_chainid():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "status": "1",
                "message": "OK",
                "result": [
                    {
                        "SourceCode": "contract BaseContract {}",
                        "ContractName": "BaseContract",
                        "CompilerVersion": "v0.8.20+commit.test",
                        "Proxy": "0",
                    }
                ],
            },
        )

    settings = Settings(etherscan_api_key="v2-key", explorer_max_retries=0)
    puller = EtherscanV2SourcePuller(settings=settings, transport=httpx.MockTransport(handler))

    result = await puller.pull(chain=Chain.BASE, address="0x0000000000000000000000000000000000000000")

    assert result.status == "verified"
    assert result.source == "contract BaseContract {}"
    assert seen["params"]["chainid"] == "8453"
    assert seen["params"]["apikey"] == "v2-key"


@pytest.mark.asyncio
async def test_etherscan_v2_missing_key_is_nonfatal():
    puller = EtherscanV2SourcePuller(settings=Settings(etherscan_api_key=None))

    result = await puller.pull(chain=Chain.ETHEREUM, address="0x0000000000000000000000000000000000000000")

    assert result.status == "missing"
    assert result.reason == "etherscan_v2_api_key_missing"
