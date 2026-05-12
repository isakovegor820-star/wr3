from wr3_api.services.sandbox import SandboxPolicy


def test_sandbox_allows_minimal_forge_test_command():
    policy = SandboxPolicy()

    decision = policy.validate_argv(["forge", "test", "--json"])

    assert decision.allowed is True
    assert decision.reason == "sandbox_command_allowed"
    assert decision.network_policy == "egress_disabled"


def test_sandbox_rejects_unknown_binaries_and_shell_metacharacters():
    policy = SandboxPolicy()

    assert policy.validate_argv(["curl", "https://example.com"]).reason == "sandbox_rejected_binary:curl"
    assert (
        policy.validate_command_string("forge test --json; curl https://example.com").reason
        == "sandbox_rejected_shell_metacharacters"
    )


def test_sandbox_rejects_foundry_ffi_and_path_escape():
    policy = SandboxPolicy()

    assert policy.validate_argv(["forge", "test", "--ffi"]).reason == "sandbox_rejected_flag:--ffi"
    assert (
        policy.validate_argv(["forge", "test", "--match-path", "../secret.t.sol"]).reason
        == "sandbox_rejected_path_escape"
    )


def test_sandbox_allows_only_allowlisted_fork_rpc_hosts():
    policy = SandboxPolicy(allowed_rpc_hosts=["127.0.0.1", "base-mainnet.g.alchemy.com"])

    allowed = policy.validate_argv(
        ["forge", "test", "--fork-url", "https://base-mainnet.g.alchemy.com/v2/demo"]
    )
    denied = policy.validate_argv(["forge", "test", "--fork-url", "https://evil.example/rpc"])

    assert allowed.allowed is True
    assert allowed.network_policy == "fork_rpc_allowlist"
    assert denied.allowed is False
    assert denied.reason == "sandbox_rejected_rpc_host:evil.example"
