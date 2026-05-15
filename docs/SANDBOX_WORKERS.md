# Sandbox Workers

Status: policy plus current local worker boundary.

## Rule

Sandbox workers must not have write access to the primary database. They receive
scoped input bundles and return signed manifests plus private artifact URIs.

## Allowed Network

Default egress is denied. The only allowed outbound hosts are configured through
`WR3_SANDBOX_ALLOWED_RPC_HOSTS`, for example:

```bash
WR3_SANDBOX_ALLOWED_RPC_HOSTS='["eth-mainnet.g.alchemy.com","base-mainnet.g.alchemy.com","arb-mainnet.g.alchemy.com","bsc-dataseed.binance.org"]'
```

## Foundry/Anvil

Required environment:

```bash
WR3_POC_MAX_ATTEMPTS=5
ETHEREUM_FORK_RPC_URL=...
BASE_FORK_RPC_URL=...
BSC_FORK_RPC_URL=...
ARBITRUM_FORK_RPC_URL=...
```

PoC attempts:

- Team/Pro and standard/deep only.
- Max 5 attempts per finding.
- Store PoC artifact or failure reason.
- Never mark confirmed unless isolated execution produces explicit success.

## Fuzzing

Medusa and ItyFuzz run only for deep Team/Pro jobs. Timeouts and resource limits
must be set per worker. Counterexamples are sensitive artifacts and private by
default.

Current tool policy:

```text
infra/sandbox/tool-policy.json
```

ItyFuzz is optional for closed beta until a trusted binary, patched upstream
build, or pinned sandbox image exists. Missing ItyFuzz must create a
`skipped_optional` artifact, not a fake result.

## Verification Before Closed Beta

Run the local evidence check:

```bash
npm run sandbox:evidence
npm run sandbox:container:evidence
```

Current local artifact:

```text
artifacts/readiness/sandbox_evidence_20260515T084422Z.md
```

Current local result: 9 passed, 0 failed.

- [x] Worker entrypoint refuses `WR3_DATABASE_URL`.
- [x] Worker entrypoint refuses secret-manager tokens.
- [x] Command policy rejects shell metacharacters.
- [x] Command policy rejects `curl` style network tooling.
- [x] Command policy rejects private-key flags.
- [x] Allowlisted fork RPC host is accepted.
- [x] Non-allowlisted fork RPC host is rejected.
- [ ] Real container/VM egress test completed on staging.
- [ ] Artifact manifests contain no raw source unless encrypted.

The checked boxes above are localhost evidence only. Before public launch, repeat
the egress and DB-write isolation checks inside the actual sandbox worker image
or VM.
