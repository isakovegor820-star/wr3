# Sandbox Worker Policy

- Default network egress: disabled.
- Allowed egress: fork RPC allowlist only, per job.
- Filesystem: ephemeral job directory.
- Secrets: no production DB credentials, no Doppler token, no analytics keys.
- Output: signed manifest plus encrypted artifacts.
- Public callers never receive raw PoC or fuzzer counterexamples.
- Generated commands must pass an allowlist before execution.

## MVP Command Allowlist

Implemented in `apps/api/wr3_api/services/sandbox.py`:

- Allowed binaries: `forge`, `anvil`, `medusa`, `ityfuzz`, `trident`.
- Allowed Foundry subcommands: `test`, `build`, `inspect`, `snapshot`.
- Blocked flags include `--ffi`, `--allow-paths`, `--unsafe`, and absolute or
  parent-directory path escapes for generated path arguments.
- RPC egress is only allowed when the URL host is in
  `WR3_SANDBOX_ALLOWED_RPC_HOSTS`.
- Commands are passed as argv arrays. Shell command strings with metacharacters
  are rejected before parsing.
