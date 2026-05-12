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

## Verification Before Closed Beta

- [ ] Sandbox cannot connect to primary Postgres.
- [ ] Sandbox cannot read app secrets.
- [ ] Sandbox egress blocks non-allowlisted hosts.
- [ ] `--ffi`, shell metacharacters, and path escapes are rejected.
- [ ] Artifact manifests contain no raw source unless encrypted.
