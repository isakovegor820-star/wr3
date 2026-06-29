"""Regression tests for the coverage/correctness review fixes (M6, M7)."""
from wr3_api.services.bounty_sources import normalize_immunefi_bounties
from wr3_api.services.fuzzing import _simple_constructor_args


# ---- M6: constructor args are read from the TARGET contract, not the first one -
def test_constructor_args_scoped_to_target_contract():
    src = """
    // A helper declared first, with a constructor type we cannot synthesise.
    contract Helper { constructor(string memory note) {} }
    contract Token { constructor(uint256 supply) {} }
    """
    # Whole-file scan grabs Helper's `string` constructor -> unsynthesisable -> None.
    assert _simple_constructor_args(src) is None
    # Scoped to Token, it reads the token's `uint256` constructor -> a default arg.
    scoped = _simple_constructor_args(src, "Token")
    assert scoped is not None and scoped != ""


# ---- M7: rotation reaches every asset of a big program, not just the first N ----
def test_per_program_rotation_reaches_all_assets():
    assets = [
        {"type": "smart_contract", "url": f"https://etherscan.io/address/0x{i:040x}"}
        for i in range(1, 7)  # 6 in-scope contracts in one mega-program
    ]
    feed = [{"project": "Mega", "slug": "mega", "maxBounty": 1_000_000, "assets": assets}]

    reached = set()
    for offset in range(6):  # successive scout cycles advance the offset
        for target in normalize_immunefi_bounties(feed, max_per_program=2, offset=offset):
            reached.add(target.address.lower())

    # Old behaviour: only the first 2 contracts were EVER reachable. Now all 6 are.
    assert len(reached) == 6
