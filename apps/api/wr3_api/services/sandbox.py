from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse


SHELL_METACHARS = frozenset({";", "|", "&", ">", "<", "`", "$", "\n", "\r"})
NETWORK_FLAGS = frozenset({"--fork-url", "--rpc-url", "--eth-rpc-url"})
DENIED_FLAGS = frozenset(
    {
        "--ffi",
        "--allow-paths",
        "--unsafe",
        "--root",
        "--lib-paths",
        "--remappings",
    }
)
PATH_VALUE_FLAGS = frozenset(
    {
        "--match-path",
        "--out",
        "--cache-path",
        "--contracts",
        "--test",
        "--config",
        "--manifest-path",
    }
)


@dataclass(frozen=True)
class SandboxCommandDecision:
    allowed: bool
    reason: str
    normalized_argv: tuple[str, ...]
    network_policy: str = "egress_disabled"
    timeout_seconds: int = 120


class SandboxPolicy:
    """Allowlist for generated audit-tool commands.

    The policy is intentionally conservative. It validates argv arrays before
    any subprocess boundary and rejects shell syntax, dangerous Foundry flags,
    path escapes, and unapproved RPC egress.
    """

    allowed_subcommands: dict[str, frozenset[str | None]] = {
        "forge": frozenset({"test", "build", "inspect", "snapshot"}),
        "anvil": frozenset({None}),
        "medusa": frozenset({"fuzz"}),
        "ityfuzz": frozenset({None, "evm", "run"}),
        "trident": frozenset({"fuzz", "test"}),
    }

    def __init__(
        self,
        *,
        allowed_rpc_hosts: list[str] | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        self.allowed_rpc_hosts = set(allowed_rpc_hosts or ["127.0.0.1", "localhost"])
        self.timeout_seconds = timeout_seconds

    def validate_command_string(self, command: str) -> SandboxCommandDecision:
        if any(char in command for char in SHELL_METACHARS):
            return SandboxCommandDecision(
                allowed=False,
                reason="sandbox_rejected_shell_metacharacters",
                normalized_argv=(),
                timeout_seconds=self.timeout_seconds,
            )
        try:
            argv = tuple(shlex.split(command))
        except ValueError:
            return SandboxCommandDecision(
                allowed=False,
                reason="sandbox_rejected_unparseable_command",
                normalized_argv=(),
                timeout_seconds=self.timeout_seconds,
            )
        return self.validate_argv(argv)

    def validate_argv(self, argv: list[str] | tuple[str, ...]) -> SandboxCommandDecision:
        normalized = tuple(str(part) for part in argv if str(part))
        if not normalized:
            return self._reject("sandbox_rejected_empty_command", normalized)
        if any(self._contains_shell_metacharacters(part) for part in normalized):
            return self._reject("sandbox_rejected_shell_metacharacters", normalized)

        binary = PurePosixPath(normalized[0]).name
        allowed_subcommands = self.allowed_subcommands.get(binary)
        if allowed_subcommands is None:
            return self._reject(f"sandbox_rejected_binary:{binary}", normalized)

        subcommand = self._first_non_flag_arg(normalized[1:])
        if subcommand not in allowed_subcommands:
            return self._reject(f"sandbox_rejected_subcommand:{binary}:{subcommand}", normalized)

        denied = sorted(set(normalized) & DENIED_FLAGS)
        if denied:
            return self._reject(f"sandbox_rejected_flag:{denied[0]}", normalized)

        path_error = self._path_escape_reason(normalized)
        if path_error:
            return self._reject(path_error, normalized)

        rpc_error = self._rpc_egress_reason(normalized)
        if rpc_error:
            return self._reject(rpc_error, normalized)

        network_policy = (
            "fork_rpc_allowlist"
            if any(self._flag_name(part) in NETWORK_FLAGS for part in normalized)
            else "egress_disabled"
        )
        return SandboxCommandDecision(
            allowed=True,
            reason="sandbox_command_allowed",
            normalized_argv=normalized,
            network_policy=network_policy,
            timeout_seconds=self.timeout_seconds,
        )

    def _reject(self, reason: str, argv: tuple[str, ...]) -> SandboxCommandDecision:
        return SandboxCommandDecision(
            allowed=False,
            reason=reason,
            normalized_argv=argv,
            timeout_seconds=self.timeout_seconds,
        )

    def _contains_shell_metacharacters(self, arg: str) -> bool:
        return any(char in arg for char in SHELL_METACHARS)

    def _first_non_flag_arg(self, args: tuple[str, ...]) -> str | None:
        for arg in args:
            if not arg.startswith("-"):
                return arg
        return None

    def _flag_name(self, arg: str) -> str:
        return arg.split("=", 1)[0]

    def _path_escape_reason(self, argv: tuple[str, ...]) -> str | None:
        for index, arg in enumerate(argv):
            if self._flag_name(arg) not in PATH_VALUE_FLAGS:
                continue
            value = None
            if "=" in arg:
                value = arg.split("=", 1)[1]
            elif index + 1 < len(argv):
                value = argv[index + 1]
            if value and self._is_path_escape(value):
                return "sandbox_rejected_path_escape"
        return None

    def _is_path_escape(self, value: str) -> bool:
        if value.startswith(("/", "~")):
            return True
        parts = PurePosixPath(value).parts
        return ".." in parts

    def _rpc_egress_reason(self, argv: tuple[str, ...]) -> str | None:
        for index, arg in enumerate(argv):
            flag = self._flag_name(arg)
            if flag not in NETWORK_FLAGS:
                continue
            value = None
            if "=" in arg:
                value = arg.split("=", 1)[1]
            elif index + 1 < len(argv):
                value = argv[index + 1]
            if not value:
                return "sandbox_rejected_missing_rpc_url"
            host = urlparse(value).hostname
            if host not in self.allowed_rpc_hosts:
                return f"sandbox_rejected_rpc_host:{host or 'missing'}"
        return None
