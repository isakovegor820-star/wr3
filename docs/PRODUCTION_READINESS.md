# Production Readiness

`npm run production:readiness` is the executable checklist for the non-local
part of wr3 v1.1.

It does not fake external readiness. It checks local code, configs, docs,
runtime routes, environment variables, and locally installed audit tools. It
prints no secret values and writes artifacts under `artifacts/readiness/`.

## Command

```bash
npm run production:readiness
```

Supporting evidence commands:

```bash
npm run secrets:readiness
npm run staging:preflight
npm run sandbox:container:evidence
npm run benchmark:curated-run
npm run beta:validation
```

Strict mode for CI or release gates:

```bash
python3 scripts/production_readiness.py --strict
```

JSON output:

```bash
python3 scripts/production_readiness.py --json
```

## Status Meanings

- `done`: code/config/doc/tool/env evidence exists.
- `partial`: wr3 has a safe interface or docs, but the real provider/tool/data is
  not connected yet.
- `blocked`: public/paid launch cannot honestly claim this is ready without an
  external action.

## Current Blocking Areas

These are expected to stay blocked until real accounts, tools, datasets, or
human review exist:

- Cloudflare D1 production account and API token. R2 is optional/blocked in
  free-only mode because Cloudflare requires a payment method to activate it.
- Secret manager flow: Doppler, OCI Vault, or 1Password. Check current machine
  posture with `npm run secrets:readiness`.
- Backup encryption and remote backup target. Free-only mode uses encrypted
  local backups plus restore drills until object storage is available.
- Solodit API access or an approved replacement corpus.
- Foundry/Anvil, Medusa, and Trident production worker installs. ItyFuzz is
  optional by `infra/sandbox/tool-policy.json` until a trusted binary or patched
  build exists.
- Full external benchmark corpora with exact commit SHAs and aggregate metrics.
  Use `npm run benchmark:curate` then `npm run benchmark:curated-run`.
- Closed beta proof: 30 interviews, 10 live scans, 3 LOI/preorders.
- Incident response drill and live bug bounty setup.
- External legal review of draft legal documents.
  Use `docs/LEGAL_REVIEW_HANDOFF.md` as the handoff package.

## User-Owned Inputs

The owner must provide or perform:

- Accounts: Cloudflare, secret manager, Sentry, Telegram, explorers/RPC,
  OpenRouter ZDR, payment provider if payments begin.
- Infrastructure: staging/prod VM, production DB, backup bucket, restore drill.
- Legal: external review before paid or public launch.
- Validation: interviews, live scans, LOI/preorders, benchmark data.

## Codex-Owned Follow-Up

Codex can continue without accounts by improving:

- Automated visual regression for `/`, `/tg`, `/dashboard`, `/disclosure`.
- Larger local benchmark adapters once datasets are cloned.
- More Solana beta detectors and fixture tests.
- More production smoke checks after accounts are configured.

## Artifact Policy

Generated readiness artifacts are local operational evidence. Do not publish them
if they include infrastructure hostnames, account identifiers, or beta customer
details.
