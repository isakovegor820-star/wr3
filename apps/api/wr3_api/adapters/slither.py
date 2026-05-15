from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from wr3_api.adapters.base import EngineAdapter, EngineRunOptions, EngineRunResult, NormalizedSource, Timer
from wr3_api.domain.enums import Chain, Exploitability, Severity
from wr3_api.domain.schemas import ContractRef, Evidence, Finding, SourceLocation, Taxonomy
from wr3_api.services.tool_paths import resolve_tool_binary


class SlitherAdapter(EngineAdapter):
    name = "slither"

    async def version(self) -> str:
        binary = resolve_tool_binary("slither")
        if not binary:
            return "slither:not-installed"
        proc = await asyncio.create_subprocess_exec(
            binary,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (stdout or stderr).decode(errors="replace").strip() or "slither:unknown"

    def supports(self, source: NormalizedSource) -> bool:
        return source.chain in {Chain.ETHEREUM, Chain.BASE, Chain.BSC, Chain.ARBITRUM}

    async def run(self, source: NormalizedSource, options: EngineRunOptions) -> EngineRunResult:
        binary = resolve_tool_binary("slither")
        if not binary:
            return EngineRunResult(engine=self.name, status="skipped", error="slither binary not installed")

        with Timer() as timer:
            with tempfile.TemporaryDirectory(prefix="wr3-slither-") as temp_dir:
                src_path = Path(temp_dir) / source.file_name
                src_path.write_text(source.source, encoding="utf-8")
                proc = await asyncio.create_subprocess_exec(
                    binary,
                    str(src_path),
                    "--json",
                    "-",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=options.timeout_seconds,
                    )
                except TimeoutError:
                    proc.kill()
                    return EngineRunResult(
                        engine=self.name,
                        status="failed",
                        error="slither timed out",
                        duration_ms=timer.duration_ms,
                    )

        raw = stdout.decode(errors="replace")
        if proc.returncode != 0 and not raw:
            return EngineRunResult(
                engine=self.name,
                status="failed",
                raw_output=raw,
                error=stderr.decode(errors="replace"),
                duration_ms=timer.duration_ms,
            )

        return EngineRunResult(
            engine=self.name,
            status="success",
            findings=self._normalize(raw, source, options.audit_id),
            raw_output=raw,
            error=stderr.decode(errors="replace") or None,
            duration_ms=timer.duration_ms,
        )

    def _normalize(self, raw: str, source: NormalizedSource, audit_id: str) -> list[Finding]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []
        detectors = payload.get("results", {}).get("detectors", [])
        findings: list[Finding] = []
        for item in detectors if isinstance(detectors, list) else []:
            title = str(item.get("check") or item.get("description") or "Slither finding")
            elements = item.get("elements") if isinstance(item.get("elements"), list) else []
            first = elements[0] if elements and isinstance(elements[0], dict) else {}
            source_mapping = first.get("source_mapping") if isinstance(first.get("source_mapping"), dict) else {}
            filename = str(source_mapping.get("filename_relative") or source.file_name)
            lines = source_mapping.get("lines") if isinstance(source_mapping.get("lines"), list) else []
            start_line = int(lines[0]) if lines else None
            end_line = int(lines[-1]) if lines else start_line
            severity = self._severity(str(item.get("impact") or item.get("severity") or "medium"))
            findings.append(
                Finding(
                    audit_id=audit_id,
                    chain=source.chain,
                    contract=ContractRef(address=source.address, name=source.contract_name, file=filename),
                    location=SourceLocation(file=filename, start_line=start_line, end_line=end_line),
                    taxonomy=Taxonomy(
                        swc=None,
                        cwe=None,
                        wr3_category=self._category(title),
                    ),
                    severity=severity,
                    confidence=0.72,
                    exploitability=Exploitability.UNKNOWN,
                    sources=[self.name],
                    evidence=Evidence(static_trace=json.dumps(item, ensure_ascii=False)[:2000]),
                    summary=title,
                    description=str(item.get("description") or title),
                    impact=str(item.get("impact") or "Static analyzer reported a potential issue."),
                    recommendation=str(item.get("recommendation") or "Review this finding manually."),
                )
            )
        return findings

    def _severity(self, value: str) -> Severity:
        normalized = value.lower()
        if normalized in {"critical", "high", "medium", "low", "info"}:
            return Severity(normalized)
        if normalized in {"optimization", "informational"}:
            return Severity.INFO
        return Severity.MEDIUM

    def _category(self, title: str) -> str:
        lowered = title.lower()
        if "reentr" in lowered:
            return "reentrancy"
        if "access" in lowered or "tx-origin" in lowered:
            return "access_control"
        if "delegatecall" in lowered or "upgrade" in lowered:
            return "upgradeability"
        return "static_analysis"
