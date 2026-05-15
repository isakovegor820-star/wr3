# Local Audit Tools Install Guide

wr3 localhost-first mode must never fail just because an external audit tool is
missing. Missing tools are reported as `skipped` and the audit pipeline keeps
running with built-in heuristics.

Check current status:

```bash
curl http://127.0.0.1:8001/v1/tools/status
```

or open:

```text
http://127.0.0.1:3001/tools
```

Safe helper script:

```bash
npm run tools:install:local -- --python-only
```

This installs Slither and Wake into an isolated ignored venv at
`artifacts/audit-tools-venv`, not into the API runtime venv. This avoids Python
dependency conflicts between audit tools and FastAPI/test dependencies. wr3
auto-detects binaries from `artifacts/audit-tools-venv/bin`; override with
`WR3_AUDIT_TOOLS_BIN_DIR` when needed.

Foundry and Aderyn require explicit opt-in:

```bash
npm run tools:install:local -- --foundry
npm run tools:install:local -- --aderyn
```

## Required For Localhost 100

### Foundry

Used for local PoC attempts and Solidity invariant tests.

```bash
brew install foundry
forge --version
anvil --version
```

If Homebrew Foundry is not available on your machine, use the official Foundry
installer only after reviewing it yourself. Do not paste private keys into wr3
and do not use `forge script --broadcast` in wr3 local mode.

### Slither

Used as the legacy/static fallback analyzer.

```bash
WR3_AUDIT_TOOLS_BIN_DIR=artifacts/audit-tools-venv/bin npm run tools:install:local -- --python-only
slither --version
```

### Aderyn

Primary EVM static-analysis path in the v1.1 architecture.

```bash
cargo install aderyn
~/.cargo/bin/aderyn --version
```

You can also use an official release binary. wr3 auto-detects binaries on
`PATH`, in `artifacts/audit-tools-venv/bin`, and in `~/.cargo/bin`.

### Wake

Secondary EVM static-analysis path.

```bash
WR3_AUDIT_TOOLS_BIN_DIR=artifacts/audit-tools-venv/bin npm run tools:install:local -- --python-only
wake --version
```

## Optional Local Tools

### Medusa

Used for fuzzing once local invariant fixtures are enabled.

```bash
brew install medusa
medusa --version
```

Install from the official `crytic/medusa` release when needed.

### ItyFuzz

Used for hybrid concrete/symbolic fuzzing.

```bash
ityfuzz --version
```

The safer build-from-source path from the official docs is:

```bash
brew install openssl z3
git clone https://github.com/fuzzland/ityfuzz.git external/tools/ityfuzz
cd external/tools/ityfuzz
git submodule update --recursive --init
cargo build --release
```

On 2026-05-14 this was attempted locally and failed inside the upstream Rust
dependency `time v0.3.34` with `E0282: type annotations needed for Box<_>`.
Keep wr3's ItyFuzz adapter as `skipped_optional` until the upstream build is
patched, a compatible Rust toolchain is pinned, or a trusted release binary is
available.

Current closed-beta policy is recorded in `infra/sandbox/tool-policy.json`:
ItyFuzz is optional, not fake-installed. Missing ItyFuzz must produce
`skipped_optional` artifacts. Foundry/Medusa remain the local fuzzing baseline
until ItyFuzz has a trusted binary, patched source build, or pinned sandbox
image.

### Trident

Used for Solana beta fuzzing.

```bash
cargo install trident-cli
trident --version
```

wr3 auto-detects `~/.cargo/bin/trident`.

### Solana test-validator

Used for local Solana beta fixtures and test-validator runs.

```bash
brew install solana
solana-test-validator --version
```

## Safety Rules

- No mainnet active actions in localhost mode.
- No private keys in `.env`.
- No `forge script --broadcast`.
- Foundry PoC/fuzzing must run only in temporary local workspaces.
- RPC egress must stay on allowlisted local/fork hosts.
