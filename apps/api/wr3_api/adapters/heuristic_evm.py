from __future__ import annotations

import re

from wr3_api.adapters.base import EngineAdapter, EngineRunOptions, EngineRunResult, NormalizedSource, Timer
from wr3_api.domain.enums import Chain, Exploitability, HumanReviewStatus, Severity
from wr3_api.domain.schemas import ContractRef, Evidence, Finding, SourceLocation, Taxonomy


class HeuristicEvmAdapter(EngineAdapter):
    name = "wr3_heuristic_evm"

    async def version(self) -> str:
        return "wr3-heuristic-evm-v0.1"

    def supports(self, source: NormalizedSource) -> bool:
        return source.chain in {Chain.ETHEREUM, Chain.BASE, Chain.BSC, Chain.ARBITRUM}

    async def run(self, source: NormalizedSource, options: EngineRunOptions) -> EngineRunResult:
        with Timer() as timer:
            findings = self._scan(source, options.audit_id)
        return EngineRunResult(
            engine=self.name,
            status="success",
            findings=findings,
            raw_output=f"heuristic_findings={len(findings)}",
            duration_ms=timer.duration_ms,
        )

    def _scan(self, source: NormalizedSource, audit_id: str) -> list[Finding]:
        lower_source = source.source.lower()
        findings: list[Finding] = []

        if "tx.origin" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Авторизация зависит от tx.origin",
                    category="access_control",
                    severity=Severity.HIGH,
                    confidence=0.82,
                    exploitability=Exploitability.LIKELY,
                    trace="Обнаружено использование tx.origin",
                    impact="Фишинговый сценарий может пройти авторизацию через промежуточный контракт.",
                    recommendation="Используйте авторизацию через msg.sender и явные проверки ролей.",
                )
            )

        if "delegatecall" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Delegatecall требует строгого контроля target-адреса",
                    category="upgradeability",
                    severity=Severity.HIGH,
                    confidence=0.72,
                    exploitability=Exploitability.THEORETICAL,
                    trace="Обнаружено использование delegatecall",
                    impact="Контролируемый или непроверенный delegatecall target может менять storage вызывающего контракта.",
                    recommendation="Ограничьте delegatecall targets и проверяйте хэши кода implementation.",
                )
            )

        if re.search(r"\.call\s*(\{|\.value)", lower_source):
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Low-level value transfer требует проверки reentrancy",
                    category="reentrancy",
                    severity=Severity.MEDIUM,
                    confidence=0.68,
                    exploitability=Exploitability.UNKNOWN,
                    trace="Обнаружен low-level call с value",
                    impact="Внешние вызовы до обновления состояния могут открыть reentrancy-баги в учёте.",
                    recommendation="Используйте checks-effects-interactions и reentrancy guard там, где это уместно.",
                )
            )

        if "selfdestruct" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="В коде есть selfdestruct-путь",
                    category="lifecycle",
                    severity=Severity.MEDIUM,
                    confidence=0.75,
                    exploitability=Exploitability.THEORETICAL,
                    trace="Обнаружено использование selfdestruct",
                    impact="Контроль жизненного цикла может навсегда удалить код или изменить системные предположения.",
                    recommendation="Удалите selfdestruct, если он явно не нужен и не закрыт access-control.",
                )
            )

        privileged_function = re.search(r"function\s+(mint|burn|sweep|withdraw|set[a-z0-9_]*)\s*\(", lower_source)
        has_common_guard = any(
            guard in lower_source
            for guard in ["onlyowner", "onlyrole", "requiresauth", "auth", "msg.sender ==", "_checkowner"]
        )
        if privileged_function and not has_common_guard:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Привилегированная функция без очевидной проверки доступа",
                    category="access_control",
                    severity=Severity.MEDIUM,
                    confidence=0.58,
                    exploitability=Exploitability.THEORETICAL,
                    trace=f"Функция {privileged_function.group(1)} обнаружена без типовых owner/role guard tokens",
                    impact="Неограниченная привилегированная функция может позволить любому caller mint, sweep или менять критичную конфигурацию.",
                    recommendation="Добавьте явные role/owner checks или задокументируйте, почему функция намеренно permissionless.",
                )
            )

        if "onlyowner" in lower_source and re.search(r"\bmint\s*\(", lower_source):
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Mint под контролем владельца влияет на централизацию",
                    category="centralization",
                    severity=Severity.LOW,
                    confidence=0.76,
                    exploitability=Exploitability.UNKNOWN,
                    trace="Обнаружен паттерн onlyOwner mint",
                    impact="Привилегированный владелец может менять предположения о supply.",
                    recommendation="Задокументируйте лимиты mint, используйте multisig или добавьте неизменяемые caps.",
                )
            )

        if not findings:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Эвристический проход не нашёл находок",
                    category="informational",
                    severity=Severity.INFO,
                    confidence=0.9,
                    exploitability=Exploitability.UNKNOWN,
                    trace="Эвристический скан завершён",
                    impact="Это не означает, что контракт безопасен; MVP-проход просто не нашёл известный паттерн.",
                    recommendation="Перед запуском проведите полный статический анализ, ИИ-триаж и ручное ревью.",
                )
            )

        return findings

    def _finding(
        self,
        source: NormalizedSource,
        audit_id: str,
        *,
        summary: str,
        category: str,
        severity: Severity,
        confidence: float,
        exploitability: Exploitability,
        trace: str,
        impact: str,
        recommendation: str,
    ) -> Finding:
        return Finding(
            audit_id=audit_id,
            chain=source.chain,
            contract=ContractRef(
                address=source.address,
                name=source.contract_name,
                file=source.file_name,
            ),
            location=SourceLocation(file=source.file_name),
            taxonomy=Taxonomy(swc=None, cwe=None, wr3_category=category),
            severity=severity,
            confidence=confidence,
            exploitability=exploitability,
            sources=[self.name],
            evidence=Evidence(static_trace=trace),
            summary=summary,
            description=trace,
            impact=impact,
            recommendation=recommendation,
            human_review_status=(
                HumanReviewStatus.PENDING
                if severity in {Severity.CRITICAL, Severity.HIGH}
                else HumanReviewStatus.NOT_REQUIRED
            ),
        )
