# Zero-Cost / Near-Zero-Cost Resource Plan

Last verified: 2026-05-12.

Goal: keep wr3 closed-beta infrastructure at `$0 fixed monthly cost` where
possible, and use pay-as-you-earn providers only after revenue exists.

## Decision

Use free fixed-cost infrastructure first:

- Cloudflare Free: DNS, Worker edge facade, D1 light metadata. R2 has included
  free monthly usage, but the Dashboard can require a billing/payment method, so
  wr3 treats R2 as optional until an adult/billing-enabled account exists.
- Oracle Cloud Always Free: main VM, Postgres 17, Redis, Celery, pgvector.
- GitHub public repo: CI, secret scanning alerts, dependency checks.
- Doppler Developer Free or OCI Vault free secrets.
- Sentry Developer Free plus Telegram self-alerts.
- Etherscan V2 Free + direct explorer fallbacks.
- Alchemy Free + public RPC fallbacks.
- Direct USDC first; Polar/Lemon only for fiat/MoR when transaction fees are acceptable.

## Free Resource Matrix

| TЗ area | Free source | Current free/near-free value | wr3 use | Risk / limit |
| --- | --- | --- | --- | --- |
| Cloudflare edge | Cloudflare Workers Free | 100k Worker requests/day; D1 Free has 5M rows read/day, 100k rows written/day, 5GB storage | Public edge facade, D1 cache/metadata | Avoid private source/findings at edge |
| Artifact storage | Local encrypted filesystem | $0, no external account | localhost/private MVP reports/raw outputs/backups | Manual off-device copy needed for disaster recovery |
| Artifact storage later | Cloudflare R2 included usage | 10GB-month, 1M Class A ops, 10M Class B ops, free egress | encrypted reports/raw outputs/backups | Requires billing/payment method in Dashboard; watch op counts |
| Main VM | Oracle Always Free Ampere A1 | 4 OCPU + 24GB RAM total, 200GB block volume | FastAPI, Postgres, Redis, Celery | Capacity can be unavailable; keep Hetzner fallback |
| Object fallback | Oracle Object Storage Always Free | 20GB object/archive storage, 50k API requests/month | backup fallback if R2 unavailable | Home-region only; request limits |
| Secrets | Doppler Developer Free | Free for 3 users; service tokens and CLI | local/prod secrets | 3 days activity logs only |
| Secrets fallback | OCI Vault Always Free | 150 Always Free secrets, free software-protected keys | backup secrets manager on Oracle | Oracle-specific lock-in |
| Error monitoring | Sentry Developer Free | 1 user, 5k errors, 5GB logs/metrics, 5M spans, 1 uptime monitor | scrubbed API errors | No team features; scrub aggressively |
| Uptime | UptimeRobot Free or Sentry uptime | Basic free monitor(s) | `/live` and `/ready` | Free checks are coarse; no sensitive URLs |
| CI | GitHub Actions public repo | Standard runners free for public repos | tests/build/benchmark smoke | Private repo has minute quota |
| Secret scanning | GitHub public repo security | Secret scanning alerts/push protection free for public repos | prevent committed secrets | Public repo required for full free benefit |
| Explorer API | Etherscan API V2 Free | 3 calls/sec, 100k calls/day, selected chains | Ethereum/Base/BSC/Arbitrum verified source | Selected chains only; attribution/limits |
| BSC fallback | BscScan Free | Free community endpoints; historical docs mention 5 calls/sec | BSC verified source fallback | BscScan keys are explorer-specific |
| RPC | Alchemy Free | 30M compute units/month, 500 CU/s throughput | EVM fork reads and normal RPC | PoC/fork usage can burn CU quickly |
| RPC fallback | PublicNode, drpc public, Ankr public | Free public RPC | degraded passive scans | Rate-limit and reliability risk |
| Telegram | Telegram Bot API | HTTP bot interface, no platform fee for bot API | `/scan`, `/watch`, alerts, Mini App entry | Need BotFather token; avoid Stars for MVP |
| LLM ZDR | OpenRouter ZDR | ZDR routing control via `provider.zdr=true` | sensitive triage/PoC prompts | Not free for paid models; keep deterministic/local fallback |
| Local LLM | Qwen/DeepSeek open-weight local path | $0 if using existing GPU | sensitive fallback | Requires hardware or rented GPU |
| Payments crypto | Direct USDC on Base/Arbitrum | No platform fee; only network gas | bootstrap invoices/manual confirmation | Manual ops and tax records required |
| Payments invoice | Request Finance Free/Freelancer | Support docs say freelancers/contractors can issue invoices free; pricing page has Free plan/trial caveats | B2B crypto invoice trail | Verify account-specific limits before relying on it |
| Fiat MoR | Polar | $0 monthly/setup; 4% + 40c per transaction | fiat fallback with tax handling | Fees only after sales; extra intl/subscription fees |
| Fiat MoR fallback | Lemon Squeezy | no monthly fee; 5% + 50c per transaction | alternative fiat fallback | Higher fees; not free per transaction |
| Legal templates | SEAL, Immunefi, disclose/dioterms | Free policies/frameworks/templates | disclosure, safe-harbor wording, VDP drafts | Not a substitute for paid legal review |
| Bench data | DeFiHackLabs | Public Foundry exploit reproductions, 689 incidents | EVM benchmark corpus | Educational only; license review before redistribution |
| Bench data | SmartBugs Curated | Public annotated Solidity vulnerability dataset | unit/integration benchmark | Dataset may be dated |
| Bench data | sealevel-attacks | Public Solana attack/protection examples | Solana beta golden fixtures | Must extend beyond sample before public claims |

## What The User Still Must Create

These are free accounts/tokens, but I cannot create them from inside the local
repo:

1. Cloudflare account and D1 resources. R2 is optional until a billing-enabled
   account exists.
2. Oracle Cloud Free Tier account and Always Free VM.
3. Doppler account or OCI Vault choice.
4. Sentry Developer project.
5. Telegram bot token from BotFather.
6. Etherscan V2 API key.
7. Alchemy free app keys.
8. OpenRouter account if paid/ZDR LLM calls are desired.
9. Polar/Lemon/Request accounts only when ready to accept payments.

## Default Bootstrap Budget

Fixed monthly infrastructure: `$0`.

Variable costs:

- Direct USDC payments: gas only.
- Polar/Lemon: only on successful fiat sale.
- OpenRouter: disabled unless paid audit or manual testing.
- Alchemy: free until CU limits are hit.

## Guardrails

- Do not put private findings/source/PoC in D1, public logs, analytics, or
  non-ZDR prompts.
- Keep free scans in degraded/static mode when quotas are exceeded.
- Use encrypted local backups in free-only mode. Use R2/OCI Object Storage
  lifecycle/retention and encrypted object writes before paid public launch.
- Do not publish legal claims based on templates; paid legal review remains a
  launch blocker.

## Evidence Links

- Cloudflare Workers/D1 pricing: https://developers.cloudflare.com/workers/platform/pricing/
- Cloudflare R2 pricing: https://developers.cloudflare.com/r2/pricing/
- Oracle Always Free resources: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- Doppler pricing: https://www.doppler.com/pricing
- Sentry pricing: https://sentry.io/pricing/
- OpenRouter ZDR: https://openrouter.ai/docs/features/zdr/
- Etherscan rate limits: https://docs.etherscan.io/resources/rate-limits
- Alchemy pricing: https://www.alchemy.com/pricing
- Telegram Bot API: https://core.telegram.org/bots/api
- Polar fees: https://docs.polar.sh/merchant-of-record/fees
- Lemon Squeezy pricing: https://www.lemonsqueezy.com/pricing
- Request Finance pricing: https://www.request.finance/pricing
- SEAL Safe Harbor: https://frameworks.securityalliance.org/safe-harbor/overview/
- Immunefi Responsible Publication: https://immunefi.com/responsible-publication
- DeFiHackLabs: https://github.com/SunWeb3Sec/DeFiHackLabs
- SmartBugs Curated: https://github.com/smartbugs/smartbugs-curated
- sealevel-attacks: https://github.com/coral-xyz/sealevel-attacks
