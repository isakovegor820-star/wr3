# Third Party Notices

This MVP uses permissive runtime libraries for the hosted application and keeps
security tools with GPL/AGPL risk behind subprocess adapter boundaries.

## Application dependencies

- Next.js, React, Tailwind CSS, lucide-react, Recharts
- FastAPI, Pydantic, Uvicorn, HTTPX, pytest
- Zod and TypeScript for shared contracts

Generate the current local inventory with:

```bash
npm run license:inventory
```

The generated CSV is written to `artifacts/licenses.csv` and must be reviewed
before public or paid launch. Python package licenses are marked
`lookup_required` until a package-index/SBOM tool is connected.

## Security tool policy

- Aderyn, Wake, Slither, Medusa, ItyFuzz, Trident, Certora, and Halmos must be
  reviewed per exact version before public launch.
- GPL/AGPL tools must run as external CLI subprocesses unless legal review
  explicitly approves a different integration pattern.
- Outputs can be normalized into wr3 findings; copied code and bundled datasets
  require license review and attribution before distribution.

## Current adapter state

- Aderyn adapter: subprocess shell, skipped when binary is not installed.
- Wake adapter: subprocess shell, skipped when binary is not installed.
- wr3 heuristic adapter: local deterministic demo signal, not a replacement for
  real static analysis.
