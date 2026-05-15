#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATASET_DIR="${ROOT_DIR}/external/benchmarks"

mkdir -p "${DATASET_DIR}"

clone_or_update() {
  local name="$1"
  local url="$2"
  local target="${DATASET_DIR}/${name}"
  if [[ -d "${target}/.git" ]]; then
    echo "[wr3-datasets] updating ${name}"
    git -C "${target}" fetch --depth=1 origin
    git -C "${target}" checkout --detach FETCH_HEAD
  else
    echo "[wr3-datasets] cloning ${name}"
    git clone --depth=1 "${url}" "${target}"
  fi
  git -C "${target}" rev-parse HEAD
}

clone_or_update "DeFiHackLabs" "https://github.com/SunWeb3Sec/DeFiHackLabs.git"
clone_or_update "smartbugs-curated" "https://github.com/smartbugs/smartbugs-curated.git"
clone_or_update "sealevel-attacks" "https://github.com/coral-xyz/sealevel-attacks.git"

echo "[wr3-datasets] inventory"
python3 "${ROOT_DIR}/scripts/external_benchmark_inventory.py"
