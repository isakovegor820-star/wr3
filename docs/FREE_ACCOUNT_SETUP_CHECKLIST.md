# Free Account Setup Checklist

This checklist converts the zero-cost plan into concrete setup tasks. Keep the
status column updated during onboarding.

| # | Account/resource | Cost target | Status | Output needed in wr3 |
| --- | --- | --- | --- | --- |
| 1 | Cloudflare account | $0 fixed | todo | Account id, R2 buckets, D1 db id, API token |
| 2 | Oracle Cloud Free Tier | $0 fixed | todo | VM public IP, SSH access, region, boot/block layout |
| 3 | Doppler Developer or OCI Vault | $0 fixed | todo | Secret project/config or vault OCIDs |
| 4 | Sentry Developer | $0 fixed | todo | `WR3_SENTRY_DSN` |
| 5 | Telegram BotFather bot | $0 fixed | todo | `WR3_TELEGRAM_BOT_TOKEN`, webhook secret |
| 6 | Etherscan V2 | $0 fixed | todo | `WR3_ETHERSCAN_API_KEY` |
| 7 | BscScan/BaseScan/Arbiscan legacy keys | $0 fixed | optional | fallback explorer keys |
| 8 | Alchemy free app | $0 fixed | todo | ETH/Base/Arbitrum/BSC RPC URLs |
| 9 | OpenRouter | $0 fixed account, paid usage | optional | ZDR API key for paid/security tests |
| 10 | Request Finance | $0 fixed if Free/Freelancer works | optional | invoice base URL/API workflow |
| 11 | Polar | $0 fixed, transaction fee only | optional | checkout product ids |
| 12 | Lemon Squeezy | $0 fixed, transaction fee only | optional | fallback checkout product ids |
| 13 | GitHub public repo | $0 fixed | todo | Actions, secret scanning, branch protection |
| 14 | UptimeRobot or Sentry uptime | $0 fixed | todo | `/live` and `/ready` monitors |

## Exact Setup Order

1. Create a public GitHub repo first so CI/secret scanning are free.
2. Create Cloudflare R2/D1 and copy ids into `infra/cloudflare/wrangler.toml`.
3. Create Oracle Always Free VM; deploy Postgres/Redis/API/Celery from
   `docs/PRODUCTION_DEPLOYMENT.md`.
4. Put all secrets in Doppler or OCI Vault. Do not paste them into repo files.
5. Create Etherscan V2 + Alchemy keys and run explorer/RPC smoke tests.
6. Create Telegram bot and configure webhook only after API URL is stable.
7. Create Sentry project and enable scrubbed DSN.
8. Enable encrypted backups to R2 and run restore drill.
9. Add Request/Polar/Lemon only when first paid beta user exists.

## Free-Tier Hard No-Go

- Do not use Telegram Stars for MVP paid audits.
- Do not enable paid Cloudflare Workers plan unless free daily requests are hit.
- Do not enable paid Sentry plan until scrubbed free quota is insufficient.
- Do not run OpenRouter for Free-tier scans.
- Do not store private audit data in Cloudflare D1.
