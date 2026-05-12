from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path

from wr3_api.adapters.base import EngineAdapter, EngineRunOptions, EngineRunResult, NormalizedSource, Timer
from wr3_api.domain.enums import Chain, Exploitability, Severity
from wr3_api.domain.schemas import ContractRef, Evidence, Finding, SourceLocation, Taxonomy


class AderynAdapter(EngineAdapter):
    name = "aderyn"

    async def version(self) -> str:
        if not shutil.which("aderyn"):
            return "aderyn:not-installed"
        proc = await asyncio.create_subprocess_exec(
            "aderyn",
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (stdout or stderr).decode(errors="replace").strip() or "aderyn:unknown"

    def supports(self, source: NormalizedSource) -> bool:
        return source.chain in {Chain.ETHEREUM, Chain.BASE, Chain.BSC, Chain.ARBITRUM}

    async def run(self, source: NormalizedSource, options: EngineRunOptions) -> EngineRunResult:
        if not shutil.which("aderyn"):
            return EngineRunResult(engine=self.name, status="skipped", error="aderyn binary not installed")

        with Timer() as timer:
            with tempfile.TemporaryDirectory(prefix="wr3-aderyn-") as temp_dir:
                src_dir = Path(temp_dir) / "src"
                src_dir.mkdir()
                (src_dir / source.file_name).write_text(source.source, encoding="utf-8")
                proc = await asyncio.create_subprocess_exec(
                    "aderyn",
                    "--output",
                    "json",
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
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []

        records = payload if isinstance(payload, list) else payload.get("issues", [])
        findings: list[Finding] = []
        for item in records if isinstance(records, list) else []:
            title = str(item.get("title") or item.get("name") or "Aderyn finding")
            severity = self._severity(str(item.get("severity") or "medium"))
            findings.append(
                Finding(
                    audit_id=audit_id,
                    chain=source.chain,
                    contract=ContractRef(
                        address=source.address,
                        name=source.contract_name,
                        file=str(item.get("filename") or source.file_name),
                    ),
                    location=SourceLocation(
                        file=str(item.get("filename") or source.file_name),
                        start_line=item.get("line"),
                        end_line=item.get("line"),
                    ),
                    taxonomy=Taxonomy(swc=None, cwe=None, wr3_category="static_analysis"),
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
        return Severity.MEDIUM
