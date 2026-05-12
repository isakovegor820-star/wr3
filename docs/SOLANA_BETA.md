# Solana Beta

Status: beta only. EVM remains MVP-first.

## Current Coverage

The local Solana path supports:

- Chain selection and Solana beta labelling in UI/API.
- Pasted source ingestion.
- Heuristic Anchor/Rust detector for:
  - unchecked account validation
  - signer/authority footguns
  - PDA-like accounts without seed constraints
  - `init_if_needed` reinitialization risk
  - signed CPI seed review
- Benchmark sample fixture at `benchmarks/fixtures/sealevel_attacks_sample.json`.

## Trident Boundary

Production Trident integration should run as an external subprocess in the
sandbox worker. It must not receive DB credentials. It receives an input bundle
and returns a signed manifest plus private artifact URIs.

## Local Test-Validator Flow

```bash
solana-test-validator --reset --quiet
anchor test --skip-local-validator
```

Required before removing beta label:

- Anchor IDL parser handles account constraints, seeds, bumps, signer, owner,
  mutability, init, close, and CPI call sites.
- Trident adapter runs on sealevel-attacks fixtures.
- False-positive rate is measured and documented.
- Reports keep Solana beta limitations visible.

## Known Limitations

- Heuristics are not a real AST parser.
- No full Trident execution in local MVP unless installed.
- No Solana mainnet active validation.
- No rescue or mainnet transactions.
