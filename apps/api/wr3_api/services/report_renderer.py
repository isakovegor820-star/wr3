from __future__ import annotations

from wr3_api.domain.schemas import AuditRecord

DISCLAIMER = (
    "ИИ-предаудит и триаж воспроизводимости. Этот отчёт не заменяет "
    "ручное ревью и не гарантирует, что контракт безопасен."
)

STATE_LABELS = {
    "created": "создан",
    "queued": "в очереди",
    "ingesting": "загрузка исходников",
    "needs_source": "нужен исходный код",
    "static_running": "статический анализ",
    "triage_running": "ИИ-триаж",
    "poc_running": "PoC-проверка",
    "fuzzing_running": "фаззинг",
    "scoring": "расчёт оценки",
    "human_review": "ручное ревью",
    "changes_requested": "нужны правки",
    "partial": "частично готово",
    "completed": "готово",
    "failed": "ошибка",
    "retrying": "повтор",
    "rejected": "отклонено",
    "terminal": "завершено",
}

SEVERITY_LABELS = {
    "critical": "критично",
    "high": "высокая",
    "medium": "средняя",
    "low": "низкая",
    "info": "инфо",
}

EXPLOITABILITY_LABELS = {
    "confirmed": "подтверждено",
    "likely": "вероятно",
    "theoretical": "теоретически",
    "unknown": "неизвестно",
    "dismissed": "отклонено",
}

POC_STATUS_LABELS = {
    "not_attempted": "не запускался",
    "failed": "не подтверждён",
    "confirmed": "подтверждён",
}

HUMAN_REVIEW_LABELS = {
    "not_required": "не требуется",
    "pending": "ожидает",
    "approved": "одобрено",
    "rejected": "отклонено",
}

VERDICT_LABELS = {
    "can_write": "можно писать",
    "too_early": "рано писать",
    "do_not_write": "не писать",
    "no_signal": "нет сигнала",
}

DEPTH_LABELS = {
    "preliminary": "предварительная",
    "standard": "стандартная",
    "deep": "глубокая",
}

VISIBILITY_LABELS = {
    "private": "приватный",
    "public": "публичный",
}

CAP_LABELS = {
    "confirmed_critical": "подтверждённая критичная находка",
    "confirmed_high": "подтверждённая находка высокой важности",
    "unverified_source": "исходный код не верифицирован",
    "upgradeable_proxy_with_eoa_owner": "обновляемый прокси с EOA-владельцем",
    "unlimited_owner_mint": "неограниченный mint у владельца",
}

LIMITATION_LABELS = {
    "demo_data": "демо-данные",
    "poc_requires_paid_tier": "PoC доступен только на платном тарифе",
    "anonymous_owner_token_required_for_private_access": "для приватного доступа нужен токен владельца",
    "zdr_required_for_security_triage": "для security-триажа требуется ZDR-маршрут",
    "openrouter_zdr_route_requested": "OpenRouter запрошен в ZDR-режиме",
    "llm_triage_provider_error_using_deterministic_fallback":
        "ИИ-провайдер не ответил, wr3 безопасно перешёл на детерминированный триаж",
    "llm_triage_disabled_using_deterministic_fallback": "ИИ-триаж выключен, используется детерминированный резерв",
    "poc_requires_standard_or_deep_depth": "PoC требует стандартную или глубокую проверку",
    "poc_no_high_or_critical_candidates": "нет находок высокой/критичной важности для PoC",
    "poc_not_confirmed_after_retry_loop": "PoC не подтвердился после безопасных локальных попыток",
    "foundry_binary_missing": "Foundry не установлен",
    "proxy_admin_owner_extraction_requires_rpc_or_explorer_metadata":
        "для извлечения proxy admin/owner нужен RPC или дополнительные explorer-данные",
    "public_page_redacts_private_findings": "публичная страница скрывает приватные находки",
    "third_party_scan_public_poc_disabled": "для стороннего скана публичный PoC выключен",
    "public_claims_require_human_review": "публичные заявления требуют ручного ревью",
    "adversarial_input_detected": "обнаружены признаки prompt-injection",
    "verified_source_pull_failed_upload_source": "не удалось подтянуть verified source, нужен исходный код",
    "raw_outputs_require_paid_tier_artifact_access": "сырые выводы требуют платный доступ владельца",
}


def _label(mapping: dict[str, str], value: object) -> str:
    raw = str(value)
    return mapping.get(raw, raw.replace("_", " "))


def _limitation_label(value: str) -> str:
    if value in LIMITATION_LABELS:
        return LIMITATION_LABELS[value]
    if value.startswith("source_pulled_from_"):
        source = value.replace("source_pulled_from_", "")
        explorer, _, rest = source.partition(":")
        chain, _, address = rest.partition(":")
        address_label = f" для {address[:8]}...{address[-6:]}" if address else ""
        chain_label = f" ({chain})" if chain else ""
        return f"исходный код подтянут из {explorer}{chain_label}{address_label}"
    if value.startswith("llm_triage_provider_http_"):
        status = value.split("http_", 1)[1].split("_", 1)[0]
        if status == "403":
            return "ИИ-провайдер отказал в доступе к модели, проверь тариф/доступ к Claude Opus 4.7"
        if status == "429":
            return "ИИ-провайдер вернул лимит запросов, wr3 безопасно перешёл на детерминированный триаж"
        return f"ИИ-провайдер вернул HTTP {status}, wr3 безопасно перешёл на детерминированный триаж"
    if "_skipped:" in value:
        engine, reason = value.split("_skipped:", 1)
        return f"{engine} пропущен: {reason}"
    if "_raw_output_artifact_requires_encryption" in value:
        return "для сохранения сырого вывода нужен ключ шифрования артефактов"
    if "_billing_verification_stub" in value:
        return "проверка тарифа пока работает в MVP-режиме"
    return value.replace("_", " ")


class ReportRenderer:
    def render_markdown(self, record: AuditRecord) -> str:
        score = record.score.final_score if record.score else "ожидает расчёта"
        lines = [
            f"# wr3 отчёт предаудита: {record.request.chain}/{record.request.address or 'исходный код'}",
            "",
            f"**Оценка:** {score}",
            f"**Состояние аудита:** {_label(STATE_LABELS, record.state)}",
            f"**Версия движка:** {record.engine_version}",
            f"**Версия методики оценки:** {record.score_version}",
            "",
            f"> {DISCLAIMER}",
            "",
            "## Кто искал ошибки",
            "",
            f"- Агент проверки: `{record._security_agent_summary().status_label}`",
            f"- Модель: `{record._security_agent_summary().model}`",
            f"- Провайдер: `{record._security_agent_summary().provider}`",
            f"- Резервный режим: `{record._security_agent_summary().fallback}`",
            "",
            record._security_agent_summary().explanation,
            "",
            "## Область проверки",
            "",
            f"- Сеть: `{record.request.chain}`",
            f"- Адрес: `{record.request.address or 'только исходный код'}`",
            f"- Глубина: `{_label(DEPTH_LABELS, record.request.requested_depth)}`",
            f"- Видимость: `{_label(VISIBILITY_LABELS, record.request.visibility)}`",
            "",
        ]

        if record.score:
            lines.extend(
                [
                    "## Разбор оценки",
                    "",
                    f"- Безопасность кода: {record.score.code_security_score}",
                    f"- Централизация: {record.score.centralization_score}",
                    f"- Ликвидность: {record.score.liquidity_score}",
                    f"- Команда/KYC: {record.score.team_kyc_score}",
                    f"- Поведение в сети: {record.score.behavior_score}",
                    f"- Применённые ограничения: {', '.join(CAP_LABELS.get(item, item) for item in record.score.caps_applied) or 'нет'}",
                    "",
                ]
            )

        primary = self._primary_finding(record)
        if primary:
            assessment = primary.disclosure_assessment
            lines.extend(
                [
                    "## Главный итог",
                    "",
                    f"- Вердикт: `{VERDICT_LABELS.get(assessment.verdict, assessment.verdict_label)}`",
                    f"- Готовность: `{assessment.readiness_label}`",
                    f"- Следующий шаг: {assessment.next_step}",
                    f"- Риск false positive: `{assessment.false_positive_risk}`",
                    "",
                    assessment.plain_explanation,
                    "",
                ]
            )

        lines.extend(["## Находки", ""])
        if not record.findings:
            lines.append("Находки пока недоступны.")
        for finding in sorted(
            record.findings,
            key=lambda item: (
                {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}[item.severity],
                -item.confidence,
            ),
        ):
            lines.extend(
                [
                    f"### {finding.summary}",
                    "",
                    f"- Важность: `{_label(SEVERITY_LABELS, finding.severity)}`",
                    f"- Уверенность: `{finding.confidence:.2f}`",
                    f"- Воспроизводимость: `{_label(EXPLOITABILITY_LABELS, finding.exploitability)}`",
                    f"- Статус PoC: `{_label(POC_STATUS_LABELS, finding.evidence.poc_status)}`",
                    f"- Категория: `{finding.taxonomy.wr3_category}`",
                    f"- Источники: `{', '.join(finding.sources)}`",
                    f"- Ручное ревью: `{_label(HUMAN_REVIEW_LABELS, finding.human_review_status)}`",
                    f"- Вердикт обращения: `{finding.disclosure_assessment.verdict_label}`",
                    f"- Готовность к disclosure: `{finding.disclosure_assessment.readiness_label}`",
                    f"- Location: `{finding.disclosure_assessment.location_label}`",
                    "",
                    f"Коротко: {finding.disclosure_assessment.plain_explanation}",
                    "",
                    f"Технически: {finding.disclosure_assessment.technical_explanation}",
                    "",
                    f"Влияние: {finding.impact}",
                    "",
                    f"Рекомендация: {finding.recommendation}",
                    "",
                ]
            )
            if finding.disclosure_assessment.manual_checklist:
                lines.extend(
                    [
                        "Что проверить руками:",
                        "",
                        *(f"- {item}" for item in finding.disclosure_assessment.manual_checklist),
                        "",
                    ]
                )
            if finding.disclosure_assessment.evidence_gaps:
                lines.extend(
                    [
                        "Чего не хватает для письма:",
                        "",
                        *(f"- {item}" for item in finding.disclosure_assessment.evidence_gaps),
                        "",
                    ]
                )

        lines.extend(
            [
                "## Ограничения",
                "",
                *(f"- {_limitation_label(limitation)}" for limitation in record.limitations),
                "",
            ]
        )
        return "\n".join(lines)

    def _primary_finding(self, record: AuditRecord):
        if not record.findings:
            return None
        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        return sorted(record.findings, key=lambda item: (severity_rank[str(item.severity)], -item.confidence))[0]

    def render_html(self, record: AuditRecord) -> str:
        markdown = self.render_markdown(record)
        paragraphs = []
        for line in markdown.splitlines():
            if line.startswith("# "):
                paragraphs.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                paragraphs.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                paragraphs.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- "):
                paragraphs.append(f"<p>{line}</p>")
            elif line.startswith("> "):
                paragraphs.append(f"<blockquote>{line[2:]}</blockquote>")
            elif line:
                paragraphs.append(f"<p>{line}</p>")
        return "<!doctype html><html><body>" + "\n".join(paragraphs) + "</body></html>"
