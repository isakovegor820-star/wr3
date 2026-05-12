# wr3-score-v0.1 Methodology

The MVP score is deterministic and versioned. Historical reports must retain
the engine version, score version, and tool versions used to calculate them.

```text
final_score =
  0.35 * code_security_score +
  0.20 * centralization_score +
  0.15 * liquidity_score +
  0.15 * team_kyc_score +
  0.15 * behavior_score
```

`code_security_score = 100 - weighted_penalty(findings)`.

Severity base penalties:

| Severity | Base penalty |
| --- | ---: |
| Critical | 45 |
| High | 25 |
| Medium | 10 |
| Low | 3 |
| Info | 0 |

Exploitability multipliers:

| Status | Multiplier |
| --- | ---: |
| confirmed | 1.00 |
| likely | 0.75 |
| theoretical | 0.45 |
| unknown | 0.25 |
| dismissed | 0.00 |

Caps:

- Any confirmed Critical finding caps final score at 39.
- Any confirmed High finding caps final score at 69.
- Unverified source caps final score at 79.
- Upgradeable proxy with EOA owner caps final score at 69.
- Mint authority or unlimited owner mint caps final score at 59.
- Safe Harbor and active bounty can add at most 5 points and never hide
  High/Critical risk.
