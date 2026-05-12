# Scoring

Score version: `wr3-score-v0.1`.

```text
final_score =
  0.35 * code_security_score +
  0.20 * centralization_score +
  0.15 * liquidity_score +
  0.15 * team_kyc_score +
  0.15 * behavior_score
```

## Severity Penalties

| Severity | Base penalty |
| --- | ---: |
| Critical | 45 |
| High | 25 |
| Medium | 10 |
| Low | 3 |
| Info | 0 |

## Exploitability Multipliers

| Exploitability | Multiplier |
| --- | ---: |
| confirmed | 1.00 |
| likely | 0.75 |
| theoretical | 0.45 |
| unknown | 0.25 |
| dismissed | 0.00 |

## Hard Caps

- Confirmed Critical: final score <= 39.
- Confirmed High: final score <= 69.
- Unverified source: final score <= 79.
- Upgradeable proxy with EOA owner: final score <= 69.
- Unlimited owner mint: final score <= 59.

Safe Harbor and active bounty can add at most 5 points and must never hide
High/Critical risk.

## Calibration

Before public benchmark claims:

1. Run at least 30 known-vulnerable and 30 known-clean/low-risk contracts.
2. Record recall, precision, false-positive reduction, PoC confirmation rate,
   time-to-report, cost-to-report, and score distribution.
3. Adjust weights only through a documented changelog entry.
4. Store score version on every report so old scores remain reproducible.

Local smoke command:

```bash
npm run calibration:scoring
```

The generated artifact is sample-only until the real monthly 60-case calibration
set is populated.
