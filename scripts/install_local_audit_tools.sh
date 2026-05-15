#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/apps/api/.venv/bin/python"
TOOLS_VENV_DIR="${ROOT_DIR}/artifacts/audit-tools-venv"
TOOLS_PYTHON_BIN="${TOOLS_VENV_DIR}/bin/python"

install_python_tools=true
install_foundry=false
install_aderyn=false

for arg in "$@"; do
  case "${arg}" in
    --all)
      install_python_tools=true
      install_foundry=true
      install_aderyn=true
      ;;
    --foundry)
      install_foundry=true
      ;;
    --aderyn)
      install_aderyn=true
      ;;
    --python-only)
      install_python_tools=true
      install_foundry=false
      install_aderyn=false
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      echo "Usage: scripts/install_local_audit_tools.sh [--python-only|--foundry|--aderyn|--all]" >&2
      exit 1
      ;;
  esac
done

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "error: API virtualenv missing at ${PYTHON_BIN}" >&2
  echo 'Run: python3 -m venv apps/api/.venv && apps/api/.venv/bin/python -m pip install -e "apps/api[dev,worker,secure]"' >&2
  exit 1
fi

if [[ "${install_python_tools}" == "true" ]]; then
  "${PYTHON_BIN}" -m venv "${TOOLS_VENV_DIR}"
  "${TOOLS_PYTHON_BIN}" -m pip install --upgrade pip
  "${TOOLS_PYTHON_BIN}" -m pip install "slither-analyzer" "eth-wake"
  echo "Installed Python audit tools into ${TOOLS_VENV_DIR}."
  echo "wr3 auto-detects binaries from artifacts/audit-tools-venv/bin."
fi

if [[ "${install_foundry}" == "true" ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "error: Homebrew is required for --foundry in this script." >&2
    exit 1
  fi
  brew install foundry
fi

if [[ "${install_aderyn}" == "true" ]]; then
  if ! command -v cargo >/dev/null 2>&1; then
    echo "error: cargo is required for --aderyn in this script." >&2
    exit 1
  fi
  cargo install aderyn
fi

echo "Local audit tool install step complete. Verify with:"
echo "  curl http://127.0.0.1:8001/v1/tools/status"
