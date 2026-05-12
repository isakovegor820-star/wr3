# Score Methodology Changelog

## wr3-score-v0.1 - 2026-05-12

- Introduced 5-axis public formula:
  - Code Security 35%
  - Tokenomics/Centralization 20%
  - Liquidity Risk 15%
  - Team/KYC 15%
  - On-chain Behavior 15%
- Added severity penalties and exploitability multipliers.
- Added hard caps for confirmed Critical, confirmed High, unverified source,
  upgradeable proxy with EOA owner, and unlimited owner mint.
- Reports store `score_version`.

## Change Rule

Any future score formula or weight change must:

1. Increment score version.
2. Record the change here.
3. Keep old report versions reproducible.
4. Re-run calibration and attach metrics artifact.
