from wr3_api.adapters.base import NormalizedSource
from wr3_api.adapters.slither import SlitherAdapter
from wr3_api.domain.enums import Chain, Severity


def test_slither_normalizes_detector_json():
    raw = """
    {
      "success": true,
      "results": {
        "detectors": [
          {
            "check": "reentrancy-eth",
            "impact": "High",
            "description": "Potential reentrancy",
            "elements": [
              {
                "source_mapping": {
                  "filename_relative": "src/Vault.sol",
                  "lines": [12, 13]
                }
              }
            ]
          }
        ]
      }
    }
    """
    findings = SlitherAdapter()._normalize(  # noqa: SLF001
        raw,
        NormalizedSource(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
            source="contract Vault {}",
            contract_name="Vault",
            file_name="src/Vault.sol",
        ),
        "audit",
    )

    assert len(findings) == 1
    assert findings[0].severity == Severity.HIGH
    assert findings[0].taxonomy.wr3_category == "reentrancy"
    assert findings[0].location.start_line == 12
