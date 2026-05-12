# Development

## Local commands

```bash
npm install
python3 -m venv apps/api/.venv
apps/api/.venv/bin/python -m pip install -e "apps/api[dev]"
npm run check
npm run benchmark:mvp
```

## Run services

```bash
apps/api/.venv/bin/uvicorn wr3_api.main:app --app-dir apps/api --reload --host 127.0.0.1 --port 8001
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001 npm run dev:web
```

## Adapter policy

Adapters must implement:

```ts
type EngineAdapter = {
  name: string;
  version(): Promise<string>;
  supports(input: AuditInput): boolean;
  run(input: NormalizedSource, opts: EngineRunOptions): Promise<EngineRunResult>;
  normalize(raw: unknown): FindingCandidate[];
};
```

When a tool supports JSON or SARIF, parse that format. Human-readable stdout can
only be stored as a debug artifact.
