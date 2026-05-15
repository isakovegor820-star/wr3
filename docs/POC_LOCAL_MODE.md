# PoC Local Mode

Run:

```bash
npm run poc:local
```

The command loads `benchmarks/fixtures/poc_cases.json`, runs the Foundry PoC
worker boundary, and writes a local report under `artifacts/poc/`.

## Behavior

- If `forge` is installed, wr3 may execute local fixture tests in a temporary
  workspace.
- If `forge` is missing, wr3 writes a `skipped` artifact instead of pretending a
  PoC was confirmed.
- Max attempts are capped by `WR3_POC_MAX_ATTEMPTS` and default to 5.
- `forge script --broadcast`, private-key flags, mnemonic flags, and unlocked
  sender flags are rejected by sandbox policy.

## Safety

PoC mode is only for local fixtures, test-validator/fork mode, or explicitly
authorized scope. It must not perform active mainnet actions.
