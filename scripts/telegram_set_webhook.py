from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    token = os.getenv("WR3_TELEGRAM_BOT_TOKEN")
    webhook_url = os.getenv("WR3_TELEGRAM_WEBHOOK_URL")
    api_base = os.getenv("NEXT_PUBLIC_API_BASE_URL")
    mini_app_url = os.getenv("WR3_TELEGRAM_MINI_APP_URL") or os.getenv("WR3_WEB_BASE_URL")
    secret_token = os.getenv("WR3_TELEGRAM_WEBHOOK_SECRET")

    if not webhook_url and mini_app_url:
        base_url = mini_app_url.removesuffix("/tg").rstrip("/")
        webhook_url = base_url + "/api/wr3/v1/telegram/webhook"
    if not webhook_url and api_base:
        webhook_url = api_base.rstrip("/") + "/v1/telegram/webhook"
    if not token:
        print("WR3_TELEGRAM_BOT_TOKEN is required", file=sys.stderr)
        return 1
    if not webhook_url:
        print("WR3_TELEGRAM_WEBHOOK_URL or NEXT_PUBLIC_API_BASE_URL is required", file=sys.stderr)
        return 1
    if not webhook_url.startswith("https://"):
        print("Telegram webhook requires HTTPS.", file=sys.stderr)
        return 1

    payload: dict[str, object] = {
        "url": webhook_url,
        "allowed_updates": ["message", "edited_message"],
        "drop_pending_updates": False,
    }
    if secret_token:
        payload["secret_token"] = secret_token

    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/setWebhook",
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
