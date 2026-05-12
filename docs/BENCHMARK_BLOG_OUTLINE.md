# Benchmark Blog Outline

Working title: "Benchmarking wr3 on real smart-contract failures"

## Goal

Publish a reproducible, non-hype benchmark that proves wr3 is useful as an AI
pre-audit and triage layer, not a replacement for human auditors.

## Structure

1. Why pre-audit automation matters for small teams.
2. What wr3 tests: static engines, LLM triage, PoC attempts, scoring.
3. Dataset selection:
   - MVP fixtures.
   - DeFiHackLabs subset.
   - SmartBugs Curated subset.
   - sealevel-attacks subset.
4. Metrics:
   - recall
   - precision
   - FP reduction
   - PoC confirmation rate
   - time-to-report
   - cost-to-report
5. Baselines:
   - raw Aderyn
   - raw Wake
   - raw Slither
   - wr3 full pipeline
6. Limitations:
   - no guarantee of completeness
   - dataset bias
   - Solana beta status
   - human review still required for paid/public High/Critical claims
7. Results table.
8. What changed after failures.
9. Repro command and artifact link.

## Repro Command

```bash
npm run benchmark:mvp
apps/api/.venv/bin/python scripts/benchmark_runner.py --fixtures benchmarks/fixtures/smartbugs_sample.json --out artifacts/benchmarks/smartbugs-sample.json
apps/api/.venv/bin/python scripts/benchmark_runner.py --fixtures benchmarks/fixtures/sealevel_attacks_sample.json --out artifacts/benchmarks/sealevel-sample.json
```

## Publication Gate

Do not publish until the benchmark artifacts are generated from a clean commit and
the claims have been reviewed for defamation and overpromising risk.
