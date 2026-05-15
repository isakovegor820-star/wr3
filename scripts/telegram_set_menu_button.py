from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    token = os.getenv("WR3_TELEGRAM_BOT_TOKEN")
    mini_app_url = os.getenv("WR3_TELEGRAM_MINI_APP_URL") or os.getenv("WR3_WEB_BASE_URL")
    if mini_app_url and not mini_app_url.rstrip("/").endswith("/tg"):
        mini_app_url = mini_app_url.rstrip("/") + "/tg"

    if not token:
        print("WR3_TELEGRAM_BOT_TOKEN is required", file=sys.stderr)
        return 1
    if not mini_app_url:
        print("WR3_TELEGRAM_MINI_APP_URL or WR3_WEB_BASE_URL is required", file=sys.stderr)
        return 1
    if not mini_app_url.startswith("https://"):
        print("Telegram Mini Apps require an HTTPS URL for production.", file=sys.stderr)
        return 1

    payload = {
        "menu_button": {
            "type": "web_app",
            "text": "Open wr3",
            "web_app": {"url": mini_app_url},
        }
    }
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/setChatMenuButton",
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
