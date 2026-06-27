from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from wr3_api.adapters.base import EngineAdapter, EngineRunOptions, EngineRunResult, NormalizedSource, Timer
from wr3_api.adapters.source_tree import materialize_source_tree
from wr3_api.domain.enums import Chain, Exploitability, Severity
from wr3_api.domain.schemas import ContractRef, Evidence, Finding, SourceLocation, Taxonomy
from wr3_api.services.tool_paths import resolve_tool_binary, tool_subprocess_env


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
                source_tree = materialize_source_tree(
                    Path(temp_dir), source.source, default_file_name=source.file_name
                )
                report_path = Path(temp_dir) / "aderyn-report.json"
                # Do NOT pass --skip-build: Aderyn compiles the sources itself
                # (managing its own solc download); skipping the build makes
                # older builds panic in the report printer. A `.json` output path
                # yields the structured report we parse below.
                proc = await asyncio.create_subprocess_exec(
                    binary,
                    str(source_tree.root),
                    "-o",
                    str(report_path),
                    "--skip-update-check",
                    cwd=temp_dir,
                    env=tool_subprocess_env(),
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
                report_written = report_path.exists()
                raw = (
                    report_path.read_text(encoding="utf-8")
                    if report_written
                    else stdout.decode(errors="replace")
                )

        if not report_written:
            return EngineRunResult(
                engine=self.name,
                status="failed",
                raw_output=stdout.decode(errors="replace"),
                error=stderr.decode(errors="replace") or "aderyn produced no report",
                duration_ms=timer.duration_ms,
            )

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
        findings: list[Finding] = []
        for bucket, severity in (("high_issues", Severity.HIGH), ("low_issues", Severity.LOW)):
            container = payload.get(bucket) or {}
            issues = container.get("issues") if isinstance(container, dict) else container
            for item in issues if isinstance(issues, list) else []:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or item.get("detector_name") or "Aderyn finding")
                detector = str(item.get("detector_name") or "")
                instances = item.get("instances") if isinstance(item.get("instances"), list) else []
                first = instances[0] if instances and isinstance(instances[0], dict) else {}
                filename = str(first.get("contract_path") or source.file_name)
                line = first.get("line_no") if isinstance(first.get("line_no"), int) else None
                findings.append(
                    Finding(
                        audit_id=audit_id,
                        chain=source.chain,
                        contract=ContractRef(address=source.address, name=source.contract_name, file=filename),
                        location=SourceLocation(file=filename, start_line=line, end_line=line),
                        taxonomy=Taxonomy(swc=None, cwe=None, wr3_category=self._category(title, detector)),
                        severity=severity,
                        confidence=0.70,
                        exploitability=Exploitability.UNKNOWN,
                        sources=[self.name],
                        evidence=Evidence(static_trace=json.dumps(item, ensure_ascii=False)[:2000]),
                        summary=title,
                        description=str(item.get("description") or title),
                        impact="Статический анализатор Aderyn отметил потенциальную проблему.",
                        recommendation="Проверьте находку Aderyn вручную.",
                    )
                )
        return findings

    def _category(self, title: str, detector: str) -> str:
        text = f"{title} {detector}".lower()
        if "reentr" in text:
            return "reentrancy"
        if "delegatecall" in text or "upgrade" in text:
            return "upgradeability"
        if "send" in text or "protect" in text or "access" in text or "owner" in text or "auth" in text:
            return "access_control"
        return "static_analysis"
