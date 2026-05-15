# Telegram Mini App

Local Mini App route:

```text
http://127.0.0.1:3001/tg
```

Production Mini App route:

```text
https://<your-domain>/tg
```

Telegram requires an HTTPS Web App URL for production. For localhost testing in
Telegram, use an HTTPS tunnel only after you are ready to expose the local app.

## What Is Implemented

- `/tg` loads Telegram's official `telegram-web-app.js` script.
- The page detects `window.Telegram.WebApp`.
- The page calls `ready()` and `expand()` when opened inside Telegram.
- The page reads `initData` and sends only the raw `initData` string to the API.
- Backend validates `initData` at `POST /v1/auth/telegram/init-data`.
- User consent is explicit before wr3 creates a Telegram-backed session.
- Mini App supports:
  - scan;
  - watch;
  - score.
- The Mini App UI is mobile-first, not a resized web dashboard:
  - compact top bar;
  - small runtime/tier status chips instead of a distracting profile banner;
  - horizontal chain chips;
  - tab-style screens for Scan / Score / Watch / More;
  - fixed bottom navigation;
  - Telegram MainButton integration;
  - compact result cards instead of raw JSON blocks.
- If opened outside Telegram, the page stays usable through localhost fallback.
- In localhost preview, Scan creates a real private audit through the API and
  returns an owner-token report link. Watch uses the Telegram workflow emulator.
- If `NEXT_PUBLIC_API_BASE_URL` points at an old tunnel while `/tg` is opened on
  localhost, the web client falls back to `http://127.0.0.1:8001` so local Mini
  App QA is not broken by stale tunnel env.
- If `/tg` is opened through a Cloudflare tunnel, the web client uses same-origin
  `/api/wr3/...` proxy routes. This allows a single free HTTPS tunnel for both
  the Mini App UI and API calls.

## Production Setup

1. Create the bot in BotFather and copy the token.
2. Deploy wr3 web/API behind HTTPS.
3. Set environment:

```bash
export WR3_TELEGRAM_BOT_TOKEN="<bot-token>"
export WR3_WEB_BASE_URL="https://<your-domain>"
export WR3_TELEGRAM_MINI_APP_URL="https://<your-domain>/tg"
```

4. Configure the menu button:

```bash
npm run telegram:menu:setup
```

5. Configure webhook for `/scan`, `/watch`, `/score` chat commands:

```bash
npm run telegram:webhook:setup
```

For temporary Cloudflare tunnel testing, the webhook can use the same web tunnel
through `/api/wr3/v1/telegram/webhook`; no separate API tunnel is required.

6. In BotFather, also configure the bot profile Mini App button/screenshots
when you are ready for public testing.

## Security Rules

- Do not trust `initDataUnsafe` on the backend.
- Backend must validate raw `Telegram.WebApp.initData`.
- No private findings, source, or PoC artifacts go to public Telegram messages.
- `/score` returns only redacted public project data.
- `/scan` creates private owner-gated audit records.

References checked on 2026-05-13:

- Telegram Mini Apps official docs: `https://core.telegram.org/bots/webapps`
- Telegram Bot API `WebAppInfo` / `setChatMenuButton`: `https://core.telegram.org/bots/api`
