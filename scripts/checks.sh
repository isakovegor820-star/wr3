#!/usr/bin/env bash
set -euo pipefail

npm run test
npm run typecheck
cd apps/api
./.venv/bin/python -m pytest
