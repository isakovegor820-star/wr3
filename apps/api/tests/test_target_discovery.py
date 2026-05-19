from wr3_api.domain.enums import Chain
from wr3_api.services.target_discovery import normalize_defillama_protocols, target_from_defillama_protocol


def test_defillama_plain_address_infers_supported_chain_from_chains():
    target = target_from_defillama_protocol(
        {
            "name": "Lido",
            "slug": "lido",
            "category": "Liquid Staking",
            "chains": ["Ethereum"],
            "address": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",
            "url": "https://lido.fi",
            "twitter": "lidofinance",
            "tvl": 33_000_000_000,
        }
    )

    assert target is not None
    assert target.chain == Chain.ETHEREUM
    assert target.security_txt_url == "https://lido.fi/.well-known/security.txt"
    assert target.security_email_guess == "security@lido.fi"
    assert "passive_scan_only_no_auto_disclosure" in target.limitations


def test_defillama_prefixed_address_maps_arbitrum():
    target = target_from_defillama_protocol(
        {
            "name": "Example",
            "slug": "example",
            "category": "Dexes",
            "chains": ["Arbitrum"],
            "address": "arbitrum:0xaf88d065e77c8cc2239327c5edb3a432268e5831",
            "url": "example.org",
        }
    )

    assert target is not None
    assert target.chain == Chain.ARBITRUM
    assert target.address == "0xaf88d065e77c8cc2239327c5edb3a432268e5831"


def test_defillama_discovery_filters_cex_unsupported_and_tvl():
    targets = normalize_defillama_protocols(
        [
            {"name": "Cex", "category": "CEX", "chains": ["Ethereum"], "address": "0x1111111111111111111111111111111111111111", "tvl": 99_000_000_000},
            {"name": "Tron", "category": "Bridge", "chains": ["Tron"], "address": "tron:TXYZ", "tvl": 40_000_000_000},
            {"name": "Low", "category": "Dexes", "chains": ["Base"], "address": "0x2222222222222222222222222222222222222222", "tvl": 10},
            {"name": "BaseGood", "category": "Dexes", "chains": ["Base"], "address": "0x3333333333333333333333333333333333333333", "tvl": 1000},
        ],
        limit=10,
        min_tvl_usd=100,
        chains=[Chain.BASE],
    )

    assert [target.protocol_name for target in targets] == ["BaseGood"]


def test_defillama_preferred_chain_can_build_per_network_targets():
    targets = normalize_defillama_protocols(
        [
            {
                "name": "Cross Chain",
                "category": "Lending",
                "chains": ["Ethereum", "Base", "Arbitrum"],
                "address": "0x5555555555555555555555555555555555555555",
                "tvl": 1000,
            }
        ],
        limit=10,
        chains=[Chain.ARBITRUM],
    )

    assert len(targets) == 1
    assert targets[0].chain == Chain.ARBITRUM
