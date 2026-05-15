# Fuzzing Local Mode

Run:

```bash
npm run fuzzing:local
```

The command loads `benchmarks/fixtures/fuzzing_cases.json`, exercises the local
fuzzing worker boundary, and writes a report under `artifacts/fuzzing/`.

## Behavior

- Foundry invariant, Medusa, and ItyFuzz are treated as subprocess tools.
- Missing tools produce `skipped` artifacts and do not break the audit pipeline.
- Timeout/resource limits are owned by the worker config and sandbox policy.
- Counterexample analysis is stored as artifact/stub metadata until real fuzzers
  are installed.

## Safety

Only local fixtures and safe fork/test mode are allowed. No generated fuzzing
command may receive raw DB write access or production secrets.
