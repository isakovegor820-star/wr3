from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from wr3_api.adapters.base import EngineAdapter, EngineRunOptions, EngineRunResult, NormalizedSource, Timer
from wr3_api.adapters.source_tree import materialize_source_tree
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import Finding
from wr3_api.services.tool_paths import resolve_tool_binary


class AderynAdapter(EngineAdapter):
    name = "aderyn"

    async def version(self) -> str:
        binary = resolve_tool_binary("aderyn")
        if not binary:
            return "aderyn:not-installed"
        proc = await asyncio.create_subprocess_exec(
            binary,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (stdout or stderr).decode(errors="replace").strip() or "aderyn:unknown"

    def supports(self, source: NormalizedSource) -> bool:
        return source.chain in {Chain.ETHEREUM, Chain.BASE, Chain.BSC, Chain.ARBITRUM}

    async def run(self, source: NormalizedSource, options: EngineRunOptions) -> EngineRunResult:
        binary = resolve_tool_binary("aderyn")
        if not binary:
            return EngineRunResult(engine=self.name, status="skipped", error="aderyn binary not installed")

        with Timer() as timer:
            with tempfile.TemporaryDirectory(prefix="wr3-aderyn-") as temp_dir:
                source_tree = materialize_source_tree(Path(temp_dir), source.source, default_file_name=source.file_name)
                proc = await asyncio.create_subprocess_exec(
                    binary,
                    "--stdout",
                    "--skip-update-check",
                    "--skip-build",
                    "--skip-cloc",
                    "--no-snippets",
                    "--src",
                    str(source_tree.root),
                    temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=options.timeout_seconds
                    )
                except TimeoutError:
                    proc.kill()
                    return EngineRunResult(
                        engine=self.name,
                        status="failed",
                        error="aderyn timed out",
                        duration_ms=timer.duration_ms,
                    )

        if proc.returncode != 0:
            return EngineRunResult(
                engine=self.name,
                status="failed",
                raw_output=stdout.decode(errors="replace"),
                error=stderr.decode(errors="replace"),
                duration_ms=timer.duration_ms,
            )

        raw = stdout.decode(errors="replace")
        return EngineRunResult(
            engine=self.name,
            status="success",
            findings=self._normalize(raw, source, options.audit_id),
            raw_output=raw,
            duration_ms=timer.duration_ms,
        )

    def _normalize(self, raw: str, source: NormalizedSource, audit_id: str) -> list[Finding]:
        # Aderyn 0.1.x emits Markdown, not JSON/SARIF. Store the raw private
        # artifact and avoid inventing structured findings from prose.
        return []
