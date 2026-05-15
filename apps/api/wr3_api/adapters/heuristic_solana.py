from __future__ import annotations

from wr3_api.adapters.base import EngineAdapter, EngineRunOptions, EngineRunResult, NormalizedSource, Timer
from wr3_api.domain.enums import Chain, Exploitability, HumanReviewStatus, Severity
from wr3_api.domain.schemas import ContractRef, Evidence, Finding, SourceLocation, Taxonomy


class HeuristicSolanaAdapter(EngineAdapter):
    name = "wr3_heuristic_solana"

    async def version(self) -> str:
        return "wr3-heuristic-solana-v0.1"

    def supports(self, source: NormalizedSource) -> bool:
        return source.chain == Chain.SOLANA

    async def run(self, source: NormalizedSource, options: EngineRunOptions) -> EngineRunResult:
        with Timer() as timer:
            findings = self._scan(source, options.audit_id)
        return EngineRunResult(
            engine=self.name,
            status="success",
            findings=findings,
            raw_output=f"solana_heuristic_findings={len(findings)}",
            duration_ms=timer.duration_ms,
        )

    def _scan(self, source: NormalizedSource, audit_id: str) -> list[Finding]:
        lower_source = source.source.lower()
        findings: list[Finding] = []

        if "uncheckedaccount" in lower_source or "accountinfo<" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Unchecked Solana account требует проверки owner и signer",
                    category="solana_account_validation",
                    severity=Severity.MEDIUM,
                    confidence=0.66,
                    exploitability=Exploitability.UNKNOWN,
                    trace="Обнаружено использование UncheckedAccount или AccountInfo",
                    impact="Невалидированные аккаунты позволяют подставить account под контролем атакующего.",
                    recommendation="Проверяйте owner, signer, mutability и ожидаемые PDA seeds для каждого unchecked account.",
                )
            )

        if (
            ("authority:" in lower_source or "admin:" in lower_source or "owner:" in lower_source)
            and "accountinfo<" in lower_source
            and "signer<" not in lower_source
        ):
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Authority account не типизирован как Signer",
                    category="solana_signer",
                    severity=Severity.MEDIUM,
                    confidence=0.68,
                    exploitability=Exploitability.UNKNOWN,
                    trace="authority/admin/owner AccountInfo обнаружен без typed constraint Signer",
                    impact="Отсутствующий signer constraint может позволить вызвать privileged instructions через произвольный account.",
                    recommendation="Используйте Signer<'info> для authorities или явно проверяйте is_signer перед привилегированными действиями.",
                )
            )

        if (
            ("#[account(mut)]" in lower_source or "accountinfo<" in lower_source)
            and "seeds" not in lower_source
            and ("config:" in lower_source or "vault:" in lower_source or "pda" in lower_source)
        ):
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="PDA-like account без явных seed constraints",
                    category="solana_pda",
                    severity=Severity.LOW,
                    confidence=0.54,
                    exploitability=Exploitability.THEORETICAL,
                    trace="mutable config/vault/PDA-like account обнаружен без очевидного seeds constraint",
                    impact="Отсутствующие seed или owner checks могут позволить подмену account в Anchor programs.",
                    recommendation="Добавьте #[account(seeds = [...], bump)] или эквивалентные owner/address constraints.",
                )
            )

        if "init_if_needed" in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="init_if_needed может привести к ошибкам reinitialization",
                    category="solana_accounting",
                    severity=Severity.MEDIUM,
                    confidence=0.62,
                    exploitability=Exploitability.THEORETICAL,
                    trace="Обнаружен constraint init_if_needed",
                    impact="Ошибки reinitialization могут сбросить state или обойти одноразовую инициализацию.",
                    recommendation="Добавьте явные проверки состояния инициализации и объясните, зачем нужен init_if_needed.",
                )
            )

        if "invoke_signed" in lower_source and "seeds" not in lower_source:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Signed CPI требует явного ревью PDA seeds",
                    category="solana_pda",
                    severity=Severity.LOW,
                    confidence=0.45,
                    exploitability=Exploitability.UNKNOWN,
                    trace="Обнаружен invoke_signed без очевидных seed constraints в данном фрагменте кода",
                    impact="Неверная проверка PDA seeds может авторизовать нежелательные действия программы.",
                    recommendation="Убедитесь, что PDA seeds, bumps и account constraints явные и покрыты тестами.",
                )
            )

        if not findings:
            findings.append(
                self._finding(
                    source,
                    audit_id,
                    summary="Эвристический Solana-проход не нашёл находок",
                    category="informational",
                    severity=Severity.INFO,
                    confidence=0.82,
                    exploitability=Exploitability.UNKNOWN,
                    trace="Эвристический Solana-скан завершён",
                    impact="Это не означает, что программа безопасна; покрытие Solana beta намеренно ограничено.",
                    recommendation="Перед деплоем запустите Anchor-тесты, Trident-фаззинг и ручное ревью.",
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
