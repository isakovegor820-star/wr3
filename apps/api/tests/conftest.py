from __future__ import annotations

import os
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

# Keep the suite hermetic regardless of a local apps/api/.env (e.g. a production
# deployment config sitting next to the code). Env vars take precedence over .env
# in pydantic-settings, so this forces a clean dev baseline — while CI can still
# override by exporting the real env var first (setdefault won't clobber it).
for _key, _value in {
    "WR3_ENVIRONMENT": "development",
    "WR3_DATABASE_URL": "",
    "WR3_LLM_PROVIDER": "disabled",
    "WR3_SCOUT_AUTOPILOT_ENABLED": "false",
    "WR3_REVIEWER_TOKEN": "",
    "WR3_TELEGRAM_BOT_TOKEN": "",
    "WR3_POC_FORK_RPC_URL": "",
    "WR3_ARTIFACT_ENCRYPTION_KEY": "",
}.items():
    os.environ.setdefault(_key, _value)

# Never read the developer's real apps/api/.env during tests — it may hold a live
# production deployment config + secrets that would leak into (and break) tests
# that delete env vars to exercise the "missing key" paths. Disabling dotenv makes
# Settings depend only on the baseline above + code defaults: fully hermetic.
from wr3_api.core.config import Settings, get_settings  # noqa: E402

Settings.model_config["env_file"] = None
get_settings.cache_clear()
