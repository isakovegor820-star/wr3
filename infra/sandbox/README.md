# wr3 Sandbox Worker

This is the production worker boundary for Foundry/Medusa/ItyFuzz/Trident jobs.
It is intentionally separate from the API runtime.

## Guarantees

- No `WR3_DATABASE_URL` is accepted.
- No secret-manager token is accepted.
- Worker runs as non-root `wr3sandbox`.
- Job filesystem is ephemeral.
- Generated commands still pass `SandboxPolicy` inside the API code.

## Build

```bash
docker build -f infra/sandbox/Dockerfile -t wr3-sandbox:local .
```

## Smoke

The container must reject DB and secret-manager credentials:

```bash
docker run --rm -e WR3_DATABASE_URL=postgresql://prod wr3-sandbox:local true
docker run --rm -e DOPPLER_TOKEN=secret wr3-sandbox:local true
```

Both commands should exit non-zero.

## Network Egress

The container template does not add broad network policy by itself because local
Docker networking differs by host. Production deployment must add one of:

- VM firewall rules that allow only approved RPC hosts.
- Kubernetes/nomad network policy.
- Docker network with explicit egress proxy.

The application-level fallback remains:

```bash
WR3_SANDBOX_ALLOWED_RPC_HOSTS='["127.0.0.1","localhost"]'
```

Any generated `--fork-url` / `--rpc-url` outside that host allowlist is rejected
before subprocess execution.
