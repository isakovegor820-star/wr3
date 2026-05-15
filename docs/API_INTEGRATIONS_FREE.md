# Free API integrations

This file tracks the zero-fixed-cost API path for wr3. The rule is simple:
run locally with no paid accounts, use public/no-key fallbacks where they are
safe, and degrade clearly when a provider key is missing.

## Runtime endpoints

- `GET /v1/integrations/status` returns sanitized provider status. It never
  returns secrets.
- `GET /v1/news/hacks?limit=25` fetches public DeFiLlama hack records without a
  key.
- `GET /v1/tools/status` remains the local audit-tool status endpoint.

## P0 audit APIs

| Provider | Free path | Current implementation |
| --- | --- | --- |
| Etherscan API V2 | One free API key for Ethereum/Base/BSC/Arbitrum source pull via `chainid`; source-code/ABI endpoints are available on all chains in the Free Tier | `EtherscanV2SourcePuller`; env `WR3_ETHERSCAN_API_KEY` |
| BaseScan/BscScan/Arbiscan legacy APIs | Optional free explorer keys | Legacy fallback only |
| RPC | PublicNode no-key fallback, env RPC URLs override | `RpcRouter`; supports Ethereum/Base/BSC/Arbitrum/Solana |
| OpenRouter ZDR | No fixed account fee; usage can cost money | Disabled by default; deterministic fallback active |
| Solodit | No confirmed public no-key API | Marked `blocked`; local RAG fallback remains active |

## P0 Telegram Mini App APIs

| Provider | Free path | Current implementation |
| --- | --- | --- |
| Telegram Bot API | Free bot token from BotFather | Webhook, commands, menu button |
| Telegram Mini Apps JS | Free hosted Telegram script | `/tg` loads `telegram-web-app.js` |
| Telegram initData verification | Free backend HMAC validation | `POST /v1/auth/telegram/init-data` |
| HTTPS endpoint | Free temporary Cloudflare tunnel locally | Current local testing path |

## P1 billing APIs

| Provider | Free path | Current implementation |
| --- | --- | --- |
| Manual USDC | No API required | Manual intent + reviewer confirmation |
| Request Finance | Free/no monthly fee path depends on account/plan | Checkout intent placeholder |
| Polar | No monthly fee, transaction fee on sale | Checkout intent placeholder |
| Lemon Squeezy | No monthly fee, transaction fee on sale | Env/config placeholder |
| TON Connect | Free SDK, network/wallet fees may apply | Manifest URL placeholder |

## P1 monitoring APIs

| Provider | Free path | Current implementation |
| --- | --- | --- |
| DeFiLlama Hacks | Public no-key API | `/v1/news/hacks` |
| RSS/RSSHub | Self-hostable/free RSS bridge | Config placeholder |
| Sentry | Free/dev tier | Config placeholder + scrubber docs |
| Uptime | Free health checks against `/health`, `/live`, `/ready` | Health endpoints live |

## P1/P2 Solana APIs

| Provider | Free path | Current implementation |
| --- | --- | --- |
| Solana RPC | PublicNode no-key fallback | `RpcRouter` |
| Solana source/IDL | Project-specific verified/IDL sources | Beta parser/detector path |
| Helius | Optional free-tier account | Config placeholder |

## P2 roadmap APIs

Forta, Tenderly, BlockSec Phalcon, GitHub OAuth, and Resend remain optional
integrations. They are represented in `/v1/integrations/status` but are not
required for localhost readiness or the Mini App MVP.

## Security rules

- Missing keys must never crash scan flow.
- Provider status must never reveal token values.
- Public RPC fallback is best-effort only; never promise SLA on it.
- OpenRouter must remain disabled unless `WR3_LLM_PROVIDER=openrouter` and a ZDR
  route is explicitly configured.
- Solodit stays blocked until legitimate API access or a license-safe import path
  exists.

## References to re-check before production

- Etherscan V2 docs: `https://docs.etherscan.io/getting-started`
- Etherscan supported chains/free source endpoints: `https://docs.etherscan.io/supported-chains`
- Etherscan rate limits: `https://docs.etherscan.io/resources/rate-limits`
- PublicNode endpoints: `https://www.publicnode.com/`
- OpenRouter ZDR docs: `https://openrouter.ai/docs/features/zdr/`
- DeFiLlama hacks API: `https://api.llama.fi/hacks`
- Telegram Mini Apps: `https://core.telegram.org/bots/webapps`
- TON Connect docs: `https://docs.ton.org/develop/dapps/ton-connect/overview`
