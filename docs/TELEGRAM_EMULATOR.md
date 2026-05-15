# Telegram Emulator

Open:

```text
http://127.0.0.1:3001/telegram-emulator
```

This page simulates Telegram commands without BotFather, webhook setup, or a
real bot token.

## Supported Commands

```text
/scan base 0x0000000000000000000000000000000000000000
/watch base 0x0000000000000000000000000000000000000000 demo
/score base 0x0000000000000000000000000000000000000000
```

`/scan` creates a real local audit through `/v1/telegram/webhook`. `/watch`
creates a local watchlist entry. `/score` reads the redacted public project
summary.

The real Mini App route is `/tg`; see `docs/TELEGRAM_MINI_APP.md`.
Production Telegram requires BotFather, `WR3_TELEGRAM_BOT_TOKEN`, webhook
secret, HTTPS, and initData verification.
