from __future__ import annotations

import subprocess
from dataclasses import dataclass

from wr3_api.services.tool_paths import resolve_tool_binary


@dataclass(frozen=True)
class ToolProbe:
    id: str
    label: str
    binary: str
    category: str
    required_for_local_100: bool
    version_args: tuple[str, ...]
    install_hint: str
    safe_scope: str


@dataclass(frozen=True)
class ToolStatus:
    id: str
    label: str
    binary: str
    category: str
    installed: bool
    required_for_local_100: bool
    path: str | None
    version: str
    status: str
    install_hint: str
    safe_scope: str


TOOL_PROBES: tuple[ToolProbe, ...] = (
    ToolProbe(
        id="foundry_forge",
        label="Foundry forge",
        binary="forge",
        category="poc",
        required_for_local_100=True,
        version_args=("--version",),
        install_hint="brew install foundry или foundryup после проверки официальной инструкции Foundry.",
        safe_scope="Только локальные fixtures, тесты или fork-mode; flags broadcast/private-key запрещены sandbox policy.",
    ),
    ToolProbe(
        id="foundry_anvil",
        label="Foundry anvil",
        binary="anvil",
        category="poc",
        required_for_local_100=False,
        version_args=("--version",),
        install_hint="Устанавливается вместе с Foundry.",
        safe_scope="Только локальный test node или RPC из allowlist.",
    ),
    ToolProbe(
        id="slither",
        label="Slither",
        binary="slither",
        category="static",
        required_for_local_100=True,
        version_args=("--version",),
        install_hint='npm run tools:install:local -- --python-only',
        safe_scope="Статический анализ через subprocess; сырой вывод хранится приватным артефактом.",
    ),
    ToolProbe(
        id="aderyn",
        label="Aderyn",
        binary="aderyn",
        category="static",
        required_for_local_100=True,
        version_args=("--version",),
        install_hint="cargo install aderyn или официальный release binary от Cyfrin.",
        safe_scope="Статический анализ через subprocess; GPL-инструмент не линкуется в proprietary modules.",
    ),
    ToolProbe(
        id="wake",
        label="Wake",
        binary="wake",
        category="static",
        required_for_local_100=True,
        version_args=("--version",),
        install_hint='npm run tools:install:local -- --python-only',
        safe_scope="Subprocess/static detector path для localhost; structured output preferred.",
    ),
    ToolProbe(
        id="medusa",
        label="Medusa",
        binary="medusa",
        category="fuzzing",
        required_for_local_100=False,
        version_args=("--version",),
        install_hint="Установить из crytic/medusa release, когда фаззинг выйдет за рамки skipped artifacts.",
        safe_scope="Только sandboxed local fixtures с timeout/resource limits.",
    ),
    ToolProbe(
        id="ityfuzz",
        label="ItyFuzz",
        binary="ityfuzz",
        category="fuzzing",
        required_for_local_100=False,
        version_args=("--version",),
        install_hint="Установить из fuzzland/ityfuzz release, когда будет включён hybrid fuzzing.",
        safe_scope="Только sandboxed local fixtures с timeout/resource limits.",
    ),
    ToolProbe(
        id="trident",
        label="Trident",
        binary="trident",
        category="solana",
        required_for_local_100=False,
        version_args=("--version",),
        install_hint="Установить Ackee Trident для Solana beta fuzzing fixtures.",
        safe_scope="Только Solana test-validator и локальные fixtures.",
    ),
    ToolProbe(
        id="solana_test_validator",
        label="Solana test-validator",
        binary="solana-test-validator",
        category="solana",
        required_for_local_100=False,
        version_args=("--version",),
        install_hint="brew install solana",
        safe_scope="Только локальный validator и fixtures для Solana beta.",
    ),
)


class ToolStatusService:
    def list_statuses(self) -> list[ToolStatus]:
        return [self._probe_tool(probe) for probe in TOOL_PROBES]

    def summary(self) -> dict[str, object]:
        statuses = self.list_statuses()
        required = [tool for tool in statuses if tool.required_for_local_100]
        installed_required = [tool for tool in required if tool.installed]
        return {
            "required_installed": len(installed_required),
            "required_total": len(required),
            "installed_total": sum(1 for tool in statuses if tool.installed),
            "missing_required": [tool.id for tool in required if not tool.installed],
            "optional_missing": [
                tool.id for tool in statuses if not tool.required_for_local_100 and not tool.installed
            ],
            "status": "ready" if len(installed_required) == len(required) else "partial",
            "tools": [tool.__dict__ for tool in statuses],
        }

    def _probe_tool(self, probe: ToolProbe) -> ToolStatus:
        path = resolve_tool_binary(probe.binary)
        if path is None:
            return ToolStatus(
                id=probe.id,
                label=probe.label,
                binary=probe.binary,
                category=probe.category,
                installed=False,
                required_for_local_100=probe.required_for_local_100,
                path=None,
                version="не установлено",
                status="missing_required" if probe.required_for_local_100 else "skipped_optional",
                install_hint=probe.install_hint,
                safe_scope=probe.safe_scope,
            )
        version = self._version(path, probe.version_args)
        is_broken = version.startswith("version_error:")
        return ToolStatus(
            id=probe.id,
            label=probe.label,
            binary=probe.binary,
            category=probe.category,
            installed=not is_broken,
            required_for_local_100=probe.required_for_local_100,
            path=path,
            version=version,
            status=(
                "broken_required"
                if is_broken and probe.required_for_local_100
                else "broken_optional"
                if is_broken
                else "installed"
            ),
            install_hint=probe.install_hint,
            safe_scope=probe.safe_scope,
        )

    def _version(self, path: str, args: tuple[str, ...]) -> str:
        try:
            result = subprocess.run(
                [path, *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=4,
            )
        except Exception as exc:  # pragma: no cover - machine-specific
            return f"version_error:{exc.__class__.__name__}"
        output = (result.stdout or result.stderr or "").strip().splitlines()
        return output[0][:240] if output else "версия установлена, но не определена"
