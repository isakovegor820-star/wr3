# Local Benchmark Guide

The localhost benchmark is a small, safe product-quality loop. It does not need
production accounts or live RPC keys.

Run:

```bash
npm run benchmark:local
```

Output artifact:

```text
artifacts/benchmarks/local-benchmark-report.json
```

Included datasets:

- `benchmarks/fixtures/defihacklabs_sample.json`
- `benchmarks/fixtures/mvp_cases.json`
- `benchmarks/fixtures/smartbugs_sample.json`
- `benchmarks/fixtures/sealevel_attacks_sample.json`

The report includes:

- dataset count;
- total cases;
- passed/failed/skipped counts;
- detected finding categories;
- recall/precision where expected categories exist;
- local tool availability;
- duration;
- cost estimate fixed at `$0` for TestClient/local deterministic runs.

External tools are allowed to be missing. The benchmark still runs through the
built-in heuristic detectors and records missing tools through the tool-status
payload.

## Curated External Subset Manifest

After syncing the public corpora, create the reproducible local subset manifest:

```bash
npm run benchmark:sync-external
npm run benchmark:curate
npm run benchmark:curated-run
```

Current artifact:

```text
artifacts/benchmarks/curated-benchmark-manifest.json
```

Current coverage:

| Dataset | Cases | Source commit |
| --- | ---: | --- |
| SmartBugs Curated | 49 | `230e649123477eff332742a59a1c7cc6dc286cab` |
| DeFiHackLabs | 60 | `e2cc0be819257db7db56a5a424babccdbb99412b` |
| sealevel-attacks | 35 | `24555d044802db4022112a94d6d70e74291a4b6d` |

Safety notes:

- The manifest stores paths and hashes, not copied exploit text.
- DeFiHackLabs entries are read-only benchmark metadata. Do not execute mainnet
  exploit scripts.
- Solana cases are for local static analysis or `solana-test-validator` only.
- Public benchmark claims must use aggregate, reproducible metrics, not isolated
  anecdotes.

`npm run benchmark:curated-run` is a safe local smoke benchmark over the curated
manifest. It runs deterministic local heuristic detectors only. Treat the output
as engineering evidence, not a public claim against GPT/Trident/Olympix/CertiK
until the static tools, LLM triage, PoC/fuzzing layers, and manual review are
included.
