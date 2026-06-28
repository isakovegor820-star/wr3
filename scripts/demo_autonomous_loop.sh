#!/usr/bin/env bash
# wr3 end-to-end demo: the full autonomous bounty-hunt loop against a LIVE chain.
#
#   scope (Immunefi-style in-scope target) -> deep analysis -> fork-PoC confirming
#   the exploit on the live deployed contract -> submission-ready packet -> owner alert
#
# Hermetic: spins up a local anvil as the "live chain", deploys a vulnerable
# Vault, and drives the real production pipeline (no external network, no real
# Telegram). The only hand-fed part is the bounty scope (an Immunefi address we
# could deploy to) — everything else is the actual platform code.
#
# Usage:  bash scripts/demo_autonomous_loop.sh
# Requires: foundry (anvil/forge/cast), the apps/api venv.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
cd "$API_DIR"
PORT="${WR3_DEMO_PORT:-8600}"
URL="http://127.0.0.1:$PORT"
# Well-known anvil dev keys (test-only, never used on a real network).
KEY0=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
KEY1=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

for bin in anvil forge cast; do
  command -v "$bin" >/dev/null 2>&1 || { echo "missing $bin (install foundry)"; exit 1; }
done

PROJ=$(mktemp -d /tmp/wr3-demo.XXXXXX); mkdir -p "$PROJ/src"
printf "[profile.default]\nsrc='src'\ntest='test'\n" > "$PROJ/foundry.toml"
cat > "$PROJ/src/Target.sol" <<'SOL'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Vault {
    mapping(address => uint256) public balances;
    function deposit() external payable { balances[msg.sender] += msg.value; }
    function withdraw() external {
        uint256 a = balances[msg.sender];
        require(a > 0, "no balance");
        (bool ok, ) = msg.sender.call{value: a}("");
        require(ok, "transfer failed");
        balances[msg.sender] = 0; // state update AFTER external call -> reentrant
    }
}
SOL

echo "════════════════════════════════════════════════════════════════"
echo " wr3 DEMO — autonomous bounty hunt against a live chain"
echo "════════════════════════════════════════════════════════════════"
echo "[1/2] 🌐 live chain (anvil) + deploying an in-scope protocol"
anvil --port "$PORT" --silent &
ANVIL=$!
trap 'kill $ANVIL 2>/dev/null; rm -rf "$PROJ"' EXIT
for _ in $(seq 1 80); do cast block-number --rpc-url "$URL" >/dev/null 2>&1 && break; done
cast block-number --rpc-url "$URL" >/dev/null 2>&1 || { echo "anvil failed to start"; exit 1; }

VAULT=$(cd "$PROJ" && forge create src/Target.sol:Vault --rpc-url "$URL" --private-key "$KEY0" --broadcast --json 2>/dev/null \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["deployedTo"])')
cast send "$VAULT" "deposit()" --value 5ether --rpc-url "$URL" --private-key "$KEY1" >/dev/null 2>&1
echo "      Vault @ $VAULT  |  honest user parked $(python3 -c "print(int('$(cast balance "$VAULT" --rpc-url "$URL")')/1e18)") ETH"
echo
echo "[2/2] 🤖 wr3 autonomous pipeline"
SRC=$(cat "$PROJ/src/Target.sol")
WR3_POC_FORK_RPC_URL="$URL" \
WR3_ARTIFACT_ENCRYPTION_KEY="$(.venv/bin/python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')" \
WR3_LLM_PROVIDER=disabled PYTHONPATH=. .venv/bin/python "$ROOT/scripts/_demo_driver.py" "$VAULT" "$SRC"
