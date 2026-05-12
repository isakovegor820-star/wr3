from wr3_api.services.contracts import (
    EIP1967_IMPLEMENTATION_SLOT,
    build_source_metadata,
    detect_proxy_info,
    source_hash,
)


def test_source_hash_is_deterministic_sha256():
    first = source_hash("contract A {}")
    second = source_hash("contract A {}")

    assert first == second
    assert first is not None
    assert len(first) == 64


def test_eip1967_proxy_detection_records_limitations():
    source = f"contract P {{ bytes32 constant SLOT = {EIP1967_IMPLEMENTATION_SLOT}; function owner() external view returns(address); }}"

    proxy = detect_proxy_info(source)

    assert proxy.is_proxy is True
    assert proxy.proxy_type == "eip1967"
    assert "eip1967_implementation_slot" in proxy.detection_sources
    assert proxy.eoa_admin_possible is True
    assert "proxy_admin_owner_extraction_requires_rpc_or_explorer_metadata" in proxy.limitations


def test_source_metadata_marks_bytecode_only_as_limited():
    metadata = build_source_metadata(source="", origin="bytecode_only", bytecode_only=True)

    assert metadata.bytecode_only is True
    assert metadata.source_origin == "bytecode_only"
    assert "proxy_detection_limited_without_verified_source" in metadata.proxy_info.limitations
