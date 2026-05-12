from __future__ import annotations

from wr3_api.domain.schemas import AuditRecord

DISCLAIMER = (
    "AI-assisted предаудит и триаж воспроизводимости. Этот отчёт не заменяет "
    "ручное ревью и не гарантирует, что контракт безопасен."
)


class ReportRenderer:
    def render_markdown(self, record: AuditRecord) -> str:
        score = record.score.final_score if record.score else "ожидает расчёта"
        lines = [
            f"# wr3 отчёт предаудита: {record.request.chain}/{record.request.address or 'исходный код'}",
            "",
            f"**Score:** {score}",
            f"**Состояние аудита:** {record.state}",
            f"**Версия engine:** {record.engine_version}",
            f"**Версия score:** {record.score_version}",
            "",
            f"> {DISCLAIMER}",
            "",
            "## Область проверки",
            "",
            f"- Сеть: `{record.request.chain}`",
            f"- Адрес: `{record.request.address or 'только исходный код'}`",
            f"- Глубина: `{record.request.requested_depth}`",
            f"- Видимость: `{record.request.visibility}`",
            "",
        ]

        if record.score:
            lines.extend(
                [
                    "## Разбор score",
                    "",
                    f"- Безопасность кода: {record.score.code_security_score}",
                    f"- Централизация: {record.score.centralization_score}",
                    f"- Ликвидность: {record.score.liquidity_score}",
                    f"- Команда/KYC: {record.score.team_kyc_score}",
                    f"- On-chain поведение: {record.score.behavior_score}",
                    f"- Применённые caps: {', '.join(record.score.caps_applied) or 'нет'}",
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
                    f"- Severity: `{finding.severity}`",
                    f"- Уверенность: `{finding.confidence:.2f}`",
                    f"- Воспроизводимость: `{finding.exploitability}`",
                    f"- PoC статус: `{finding.evidence.poc_status}`",
                    f"- Категория: `{finding.taxonomy.wr3_category}`",
                    f"- Источники: `{', '.join(finding.sources)}`",
                    f"- Human review: `{finding.human_review_status}`",
                    "",
                    f"Impact: {finding.impact}",
                    "",
                    f"Рекомендация: {finding.recommendation}",
                    "",
                ]
            )

        lines.extend(
            [
                "## Ограничения",
                "",
                *(f"- {limitation}" for limitation in record.limitations),
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
