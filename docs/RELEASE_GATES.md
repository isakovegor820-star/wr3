# Release Gates G1-G6

Last updated: 2026-05-12

| Gate | Status | Evidence | Exit criteria |
| --- | --- | --- | --- |
| G1 Architecture freeze | partial | State machine, schemas, adapter interface, Postgres schema, Celery boundary, artifact vault, docs | Production deploy dry run completed |
| G2 Signal gate | partial | Static adapters, heuristics, triage consensus, benchmark runner | 30 test contracts with at least 20 useful findings and documented precision/recall |
| G3 PoC economics | partial | Team/Pro/deep PoC gate, max 5 attempts, local worker boundary | 50 test findings with median time/cost within tier caps |
| G4 Safety gate | partial | Passive default, public redaction, sensitive artifact encryption refusal, sandbox policy tests | Container egress test and no-sensitive-log review complete |
| G5 Closed beta | todo | Local MVP ready | 10 invited projects, <=10% failed scans, reports marked useful by testers |
| G6 Public launch | blocked | Draft legal docs, launch checklist | Paid legal review, benchmark blog data, support/IR ready |

## Launch Rule

Public claims, public High/Critical findings, paid audit reports, and marketing
benchmarks must not launch until G4 and the legal review part of G6 pass.
