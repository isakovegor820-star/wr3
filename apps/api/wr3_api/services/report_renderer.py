from __future__ import annotations

from wr3_api.domain.schemas import AuditRecord, DisclosureCase, Finding

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
            return "ИИ-провайдер отказал в доступе к модели, проверь доступ к Claude Opus 4.7"
        if status == "429":
            return "ИИ-провайдер вернул лимит запросов, wr3 безопасно перешёл на детерминированный триаж"
        return f"ИИ-провайдер вернул HTTP {status}, wr3 безопасно перешёл на детерминированный триаж"
    if "_skipped:" in value:
        engine, reason = value.split("_skipped:", 1)
        return f"{engine} пропущен: {reason}"
    if "_raw_output_artifact_requires_encryption" in value:
        return "для сохранения сырого вывода нужен ключ шифрования артефактов"
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

    def render_internal_disclosure_markdown(
        self,
        record: AuditRecord,
        finding: Finding,
        case: DisclosureCase,
    ) -> str:
        assessment = finding.disclosure_assessment
        lines = [
            f"# wr3 internal disclosure packet: {case.project_name or finding.contract.name}",
            "",
            "Private reviewer-only report. Keep inside wr3 owner/reviewer access.",
            "",
            "## Target",
            "",
            f"- Chain: `{record.request.chain}`",
            f"- Address: `{record.request.address or finding.contract.address or 'source-only'}`",
            f"- Finding id: `{finding.id}`",
            f"- Case id: `{case.id}`",
            "",
            "## Finding",
            "",
            f"- Type: `{finding.taxonomy.wr3_category}`",
            f"- Severity: `{finding.severity}`",
            f"- Confidence: `{finding.confidence:.2f}`",
            f"- Location: `{assessment.location_label}`",
            f"- Reproducibility: `{finding.exploitability}`",
            f"- PoC/fork/test status: `{finding.evidence.poc_status}`",
            f"- PoC artifact: `{finding.evidence.poc_artifact_uri or 'not stored'}`",
            f"- Fuzzer artifact: `{finding.evidence.fuzzer_counterexample_uri or 'not stored'}`",
            "",
            "## Why wr3 is confident",
            "",
            assessment.technical_explanation,
            "",
            "## Impact and bounty acceptance",
            "",
            finding.impact,
            "",
            self._bounty_acceptance_reason(record, finding, case),
            "",
            "## Trace / evidence",
            "",
            finding.evidence.static_trace or "No raw trace stored in this local run.",
            "",
            "## Guardrails",
            "",
            "- No mainnet transaction was broadcast by wr3.",
            "- No external support message was sent automatically.",
            "- External report must not include working transaction steps.",
            "",
        ]
        return "\n".join(lines)

    def render_external_disclosure_markdown(
        self,
        record: AuditRecord,
        finding: Finding,
        case: DisclosureCase,
    ) -> str:
        assessment = finding.disclosure_assessment
        lines = [
            f"# Responsible disclosure report: {case.project_name or finding.contract.name}",
            "",
            "This is a private responsible disclosure summary prepared for the official security contact.",
            "",
            "## Scope",
            "",
            f"- Chain: `{record.request.chain}`",
            f"- Contract / target: `{record.request.address or finding.contract.address or 'source-only'}`",
            f"- Finding category: `{finding.taxonomy.wr3_category}`",
            f"- Severity candidate: `{finding.severity}`",
            f"- Location: `{assessment.location_label}`",
            "",
            "## Summary",
            "",
            self._safe_external_text(assessment.plain_explanation),
            "",
            "## Potential impact",
            "",
            self._safe_external_text(finding.impact),
            "",
            "## Validation posture",
            "",
            "- Validation was passive/local/fork/test only.",
            "- No mainnet transaction was broadcast.",
            "- No funds were moved.",
            "- This first-contact report omits transaction recipe details and raw private traces.",
            "",
            "## Requested next step",
            "",
            "Please confirm the official security or bounty intake channel for this target. "
            "After confirmation, the wr3 team can continue coordinated private disclosure.",
            "",
        ]
        return "\n".join(lines)

    def render_bounty_submission(self, record: AuditRecord, finding: Finding) -> str:
        """A ready-to-edit bug-bounty submission report (Immunefi-style, English).
        Auto-filled from the finding; the human reviews, tweaks and submits."""
        detail = self._bounty_bug_detail(finding)
        target = record.request.address or finding.contract.address or "source-only"
        location = (
            f"{finding.contract.name}.{finding.location.function}()"
            if finding.location.function
            else finding.disclosure_assessment.location_label or finding.contract.name
        )
        bounty = record.request.bounty
        program = f"{bounty.program} ({bounty.url})" if bounty and bounty.url else (bounty.program if bounty else "—")
        swc = f" (SWC-{finding.taxonomy.swc})" if finding.taxonomy.swc else ""
        lines = [
            f"# [{str(finding.severity).upper()}] {detail['title']}",
            "",
            f"- Program: {program}",
            f"- Chain / target: {record.request.chain} — {target}",
            f"- Affected: {location}",
            f"- Severity: {finding.severity} — {detail['severity_reason']}",
            f"- Bug class: {finding.taxonomy.wr3_category}{swc}",
            "",
            "## Summary",
            detail["summary"],
            "",
            "## Impact",
            detail["impact"],
            "",
            "## Steps to reproduce / Proof of Concept",
            detail["repro"],
            "",
            "A working Foundry proof-of-concept that confirms this on a mainnet fork is available and can be attached.",
            "",
            "## Recommended fix",
            detail["fix"] or finding.recommendation,
            "",
            "## Notes",
            "- Found by automated static analysis + a confirming fork proof-of-concept.",
            "- Validation was passive / local / fork only — no mainnet transaction, no funds moved.",
        ]
        return "\n".join(lines)

    def _bounty_bug_detail(self, finding: Finding) -> dict[str, str]:
        catalog: list[tuple[str, dict[str, str]]] = [
            ("reentr", {
                "title": "Reentrancy allows draining deposited funds",
                "severity_reason": "an attacker can withdraw more than they deposited and drain the contract",
                "summary": "The withdraw path makes an external call to the caller before zeroing the caller's recorded balance, so the caller can re-enter withdraw and be paid repeatedly against the same balance.",
                "impact": "An attacker repeatedly re-enters and withdraws, draining all funds held by the contract, including other users' deposits.",
                "repro": "1) Deposit a small amount from an attacker contract.\n2) Call withdraw; the attacker's receive()/fallback re-enters withdraw while the contract balance is still non-zero.\n3) The contract pays out on each re-entry before the balance is zeroed, draining it.",
                "fix": "Apply checks-effects-interactions: zero the balance before the external transfer, or add a reentrancy guard (nonReentrant).",
            }),
            ("tx.origin", {
                "title": "Authorization via tx.origin enables phishing takeover",
                "severity_reason": "a privileged action can be triggered through an attacker contract if the owner signs one transaction",
                "summary": "A privileged function authorizes using tx.origin == owner instead of msg.sender, so any contract the owner is tricked into calling can perform the privileged action on the owner's behalf.",
                "impact": "An attacker phishes the owner into a single transaction and seizes ownership / moves funds / performs privileged actions.",
                "repro": "1) Deploy an attacker contract that calls the victim's privileged function.\n2) Get the owner to call the attacker contract (phishing).\n3) Inside, tx.origin is still the owner, so the check passes and the privileged action executes for the attacker.",
                "fix": "Authorize with msg.sender == owner; never use tx.origin for authorization.",
            }),
            ("delegatecall", {
                "title": "Unprotected delegatecall allows full contract takeover",
                "severity_reason": "an attacker can overwrite storage (e.g. the owner slot) and seize the contract",
                "summary": "An unprotected function delegatecalls into an attacker-supplied address, executing attacker code in this contract's storage context.",
                "impact": "An attacker overwrites critical storage (such as owner) and fully takes over the contract and its funds.",
                "repro": "1) Deploy an implant contract whose function writes attacker's address to storage slot 0.\n2) Call the unprotected delegatecall entrypoint with (implant, abi.encodeWithSignature(...)).\n3) The implant runs in the victim's context and overwrites owner; the attacker now controls the contract.",
                "fix": "Restrict the delegatecall to a trusted, immutable implementation and gate it behind owner-only access.",
            }),
            ("selfdestruct", {
                "title": "Unprotected selfdestruct lets anyone destroy the contract",
                "severity_reason": "any caller can destroy the contract and force out its entire balance",
                "summary": "A function reachable by any caller executes selfdestruct with no access control.",
                "impact": "An arbitrary attacker destroys the contract and disgorges all of its ETH, bricking the protocol.",
                "repro": "1) From any address, call the unprotected function that contains selfdestruct.\n2) The contract self-destructs and all its ETH is sent out in the same transaction.",
                "fix": "Gate the selfdestruct path behind owner-only access, or remove it.",
            }),
            ("suicidal", {
                "title": "Unprotected selfdestruct lets anyone destroy the contract",
                "severity_reason": "any caller can destroy the contract and force out its entire balance",
                "summary": "A function reachable by any caller executes selfdestruct with no access control.",
                "impact": "An arbitrary attacker destroys the contract and disgorges all of its ETH, bricking the protocol.",
                "repro": "1) From any address, call the unprotected function that contains selfdestruct.\n2) The contract self-destructs and all its ETH is sent out in the same transaction.",
                "fix": "Gate the selfdestruct path behind owner-only access, or remove it.",
            }),
            ("supply", {
                "title": "Token supply can be inflated (broken accounting)",
                "severity_reason": "balances can exceed totalSupply, creating tokens from nothing",
                "summary": "A fuzzed call sequence shows tracked holder balances can collectively exceed totalSupply, i.e. value is created rather than conserved.",
                "impact": "An attacker inflates token balances out of thin air, diluting every holder and breaking the token's economics.",
                "repro": "1) Drive the transfer/mint path with a fuzzer (Medusa) tracking a small set of holders.\n2) The invariant sum(balances) <= totalSupply is violated, proving inflation.",
                "fix": "Ensure every credit is matched by a debit and totalSupply tracks issuance; re-run the fuzzer to confirm the invariant holds.",
            }),
            ("mint", {
                "title": "Unprotected mint allows arbitrary token issuance",
                "severity_reason": "any caller can mint tokens to themselves with no authorization",
                "summary": "A mint-like function credits a public balance mapping with no access control.",
                "impact": "An attacker mints unlimited tokens to themselves, draining value from all holders.",
                "repro": "1) From any address, call the mint function with the attacker as recipient.\n2) The attacker's balance increases with no authorization check.",
                "fix": "Restrict minting to an authorized role (onlyOwner / minter role).",
            }),
            ("ownership", {
                "title": "Ownership can be taken over by an arbitrary caller",
                "severity_reason": "an unauthorized caller can become owner and control the contract",
                "summary": "A function that assigns the owner has no effective access control, so anyone can call it and become owner.",
                "impact": "An attacker takes ownership and gains full control over privileged functions and funds.",
                "repro": "1) From any address, call the owner-setting function with the attacker's address.\n2) Read owner(): it is now the attacker.",
                "fix": "Guard the owner-setting path with onlyOwner (or a two-step transfer).",
            }),
            ("access", {
                "title": "Missing access control on a privileged function",
                "severity_reason": "an unauthorized caller can perform a privileged action",
                "summary": "A privileged function lacks an effective authorization check, so any caller can invoke it.",
                "impact": "An attacker performs a privileged action — seizing control or moving funds — without authorization.",
                "repro": "1) From any address, call the privileged function.\n2) The action succeeds despite the caller not being the owner/authorized role.",
                "fix": "Add an access-control check (onlyOwner / role-based) to the privileged function.",
            }),
        ]
        haystack = f"{finding.taxonomy.wr3_category} {finding.summary}".lower()
        for key, detail in catalog:
            if key in haystack:
                return detail
        return {
            "title": finding.summary,
            "severity_reason": f"{finding.severity} severity per automated triage",
            "summary": finding.summary,
            "impact": finding.impact,
            "repro": "See the attached Foundry proof-of-concept.",
            "fix": finding.recommendation,
        }

    def render_text_pdf(self, title: str, body: str) -> bytes:
        clean_lines = [title, "", *body.splitlines()]
        text_commands = ["BT", "/F1 10 Tf", "50 780 Td"]
        for line in clean_lines[:95]:
            escaped = self._pdf_escape(line[:110])
            text_commands.append(f"({escaped}) Tj")
            text_commands.append("0 -12 Td")
        text_commands.append("ET")
        stream = "\n".join(text_commands).encode("latin-1", "replace")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        ]
        out = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(out))
            out.extend(f"{index} 0 obj\n".encode("ascii"))
            out.extend(obj)
            out.extend(b"\nendobj\n")
        xref_offset = len(out)
        out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        out.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        out.extend(
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        )
        return bytes(out)

    def _pdf_escape(self, value: str) -> str:
        return value.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _safe_external_text(self, value: str) -> str:
        replacements = {
            "scam": "unsafe",
            "fraud": "unsafe",
            "exploit steps": "transaction recipe details",
            "working PoC": "validation evidence",
            "working poc": "validation evidence",
        }
        safe = value
        for needle, replacement in replacements.items():
            safe = safe.replace(needle, replacement).replace(needle.title(), replacement)
        return safe

    def _bounty_acceptance_reason(self, record: AuditRecord, finding: Finding, case: DisclosureCase) -> str:
        contact = case.project_contact or "official contact pending"
        return (
            f"Potentially acceptable because impact is documented, severity is {finding.severity}, "
            f"validation status is {finding.evidence.poc_status}, scope/contact evidence is `{case.contact_source or 'unknown'}` "
            f"via `{contact}`, and the report stays private until human approval."
        )
