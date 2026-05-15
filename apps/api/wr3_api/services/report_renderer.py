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
    "llm_triage_disabled_using_deterministic_fallback": "ИИ-триаж выключен, используется детерминированный резерв",
    "poc_requires_standard_or_deep_depth": "PoC требует стандартную или глубокую проверку",
    "poc_no_high_or_critical_candidates": "нет находок высокой/критичной важности для PoC",
    "foundry_binary_missing": "Foundry не установлен",
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
        return f"исходный код подтянут из {value.replace('source_pulled_from_', '')}"
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
                    "",
                    f"Влияние: {finding.impact}",
                    "",
                    f"Рекомендация: {finding.recommendation}",
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
