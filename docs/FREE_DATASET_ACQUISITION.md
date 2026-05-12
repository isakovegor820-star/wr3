# Free Dataset Acquisition Plan

Status: actionable plan for benchmark/QA without paid datasets.

## Datasets

| Dataset | Source | Cost | Use | Local path |
| --- | --- | --- | --- | --- |
| DeFiHackLabs | https://github.com/SunWeb3Sec/DeFiHackLabs | free/public | EVM historical exploit replay | `external/DeFiHackLabs` |
| SmartBugs Curated | https://github.com/smartbugs/smartbugs-curated | free/public | labeled Solidity vulnerabilities | `external/smartbugs-curated` |
| sealevel-attacks | https://github.com/coral-xyz/sealevel-attacks | free/public | Solana Anchor footguns | `external/sealevel-attacks` |
| Live verified contracts | Etherscan V2 free API + explorer pages | free within quota | fresh real-world scan QA | `artifacts/benchmarks/live-contracts.json` |

## Acquisition Commands

```bash
mkdir -p external
git clone --depth 1 https://github.com/SunWeb3Sec/DeFiHackLabs external/DeFiHackLabs
git clone --depth 1 https://github.com/smartbugs/smartbugs-curated external/smartbugs-curated
git clone --depth 1 https://github.com/coral-xyz/sealevel-attacks external/sealevel-attacks
```

`external/` must stay gitignored unless a specific sanitized fixture is copied
into `benchmarks/fixtures/`.

## Public Claim Rule

Do not publish wr3 recall/precision claims from sample fixtures. Public claims
require:

- 100 DeFiHackLabs subset cases or a documented smaller beta subset.
- SmartBugs Curated subset.
- sealevel-attacks subset.
- Stored metrics artifact.
- Methodology notes with dataset commit hashes.
- Human review of wording before publication.

## License Handling

Before redistributing any copied source/test case:

1. Record repository URL and commit hash.
2. Check license file.
3. Prefer storing derived metrics over copying large copyrighted reports.
4. Keep exploit PoCs private/internal unless license and disclosure policy allow
   public reuse.
