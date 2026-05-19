import type { AuditSummary, Finding } from "@wr3/shared";
import { AlertTriangle, CheckCircle2, ClipboardList, FileSearch, ShieldAlert } from "lucide-react";
import { tLimitation } from "@/lib/i18n";

const severityRank: Record<Finding["severity"], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4
};

function primaryFinding(findings: Finding[]): Finding | null {
  return [...findings].sort(
    (left, right) => severityRank[left.severity] - severityRank[right.severity] || right.confidence - left.confidence
  )[0] ?? null;
}

function verdictTone(verdict: string) {
  if (verdict === "can_write") return "ready";
  if (verdict === "do_not_write") return "blocked";
  if (verdict === "no_signal") return "quiet";
  return "warning";
}

function humanVerdict(audit: AuditSummary, findings: Finding[]) {
  const primary = primaryFinding(findings);
  if (!primary) {
    return {
      verdict: "no_signal",
      label: "Пока нет явных сигналов",
      meaning: "wr3 не нашёл кандидатных багов в этом проходе. Это не гарантия безопасности, а результат текущей глубины проверки.",
      next: "Если цель важная, запусти глубокий режим и ручной review."
    };
  }

  const assessment = primary.disclosure_assessment;
  if (assessment.verdict === "can_write") {
    return {
      verdict: assessment.verdict,
      label: "Можно готовить приватный report",
      meaning: "У wr3 есть достаточно сильный сигнал: подтверждение PoC/fork-test или сильная связка static+AI. Писать можно только приватно и только в официальный security contact.",
      next: assessment.next_step
    };
  }
  if (assessment.verdict === "do_not_write") {
    return {
      verdict: assessment.verdict,
      label: "Не писать",
      meaning: "Сигнал отклонён или похож на false positive. Такой результат нельзя отправлять как bug report.",
      next: assessment.next_step
    };
  }
  return {
    verdict: assessment.verdict,
    label: "Рано писать",
    meaning:
      "wr3 увидел подозрительный паттерн, но пока не доказал, что это настоящая уязвимость. Это задача для проверки, а не готовый bug bounty report.",
    next: assessment.next_step || "Сначала нужна ручная проверка, точная location и независимое подтверждение."
  };
}

function automationRows(audit: AuditSummary, findings: Finding[]) {
  const hasConfirmedPoc = findings.some((finding) => finding.evidence.poc_status === "confirmed");
  const hasKnownLocation = findings.some(
    (finding) => finding.disclosure_assessment.location_status === "known" || finding.location.start_line || finding.location.function
  );
  const llmFallback = audit.limitations.some((item) => item.includes("llm_triage_provider") || item.includes("deterministic_fallback"));
  const staticFailed = audit.static_analysis_status === "failed" || audit.failed_stages.some((item) => item.startsWith("static:"));

  return [
    {
      label: audit.source_metadata.bytecode_only ? "Source не подтверждён" : "Source получен",
      value: audit.source_metadata.bytecode_only
        ? "Анализ ограничен bytecode-only режимом."
        : "Можно читать исходники и строить объяснение.",
      state: audit.source_metadata.bytecode_only ? "warning" : "done"
    },
    {
      label: audit.static_analysis_status === "success" ? "Static tools прошли" : "Static tools частично",
      value: staticFailed
        ? "Часть движков упала, поэтому сигнал нельзя считать доказанным."
        : "Статический слой дал usable signal.",
      state: staticFailed ? "warning" : "done"
    },
    {
      label: llmFallback ? "ИИ не подтвердил" : "ИИ-триаж прошёл",
      value: llmFallback
        ? "OpenRouter/ZDR не дал полноценный ответ, использован безопасный fallback."
        : "4-agent triage смог обработать finding.",
      state: llmFallback ? "warning" : "done"
    },
    {
      label: hasKnownLocation ? "Location найдена" : "Location пустая",
      value: hasKnownLocation
        ? "Есть файл/строка/функция для проверки."
        : "Нужно найти точное место в коде перед любым письмом.",
      state: hasKnownLocation ? "done" : "warning"
    },
    {
      label: hasConfirmedPoc ? "PoC подтверждён" : "PoC не подтверждён",
      value: hasConfirmedPoc
        ? "Можно собирать приватный report."
        : "Нельзя писать как о доказанной уязвимости.",
      state: hasConfirmedPoc ? "done" : "warning"
    }
  ];
}

function agentTone(status: string) {
  if (status === "provider_confirmed") return "done";
  if (status === "disabled" || status === "fallback") return "warning";
  return "warning";
}

function topBlockers(audit: AuditSummary, findings: Finding[]) {
  const primary = primaryFinding(findings);
  const gaps = primary?.disclosure_assessment.evidence_gaps ?? [];
  const translatedLimitations = audit.limitations
    .filter((item) =>
      item.includes("llm_triage") ||
      item.includes("poc_not_confirmed") ||
      item.includes("fuzzing") ||
      item.includes("source") ||
      item.includes("zdr")
    )
    .map(tLimitation);
  return [...gaps, ...translatedLimitations].slice(0, 5);
}

export function AuditInterpretationPanel({ audit, findings }: { audit: AuditSummary; findings: Finding[] }) {
  const result = humanVerdict(audit, findings);
  const tone = verdictTone(result.verdict);
  const blockers = topBlockers(audit, findings);
  const rows = automationRows(audit, findings);

  return (
    <section className={`panel audit-meaning-panel audit-meaning-${tone}`}>
      <div className="audit-meaning-main">
        <div className="audit-meaning-title">
          {tone === "ready" ? <CheckCircle2 aria-hidden="true" size={22} /> : <ShieldAlert aria-hidden="true" size={22} />}
          <div>
            <p className="eyebrow">Как понимать ответ wr3</p>
            <h2>{result.label}</h2>
          </div>
        </div>
        <p>{result.meaning}</p>
        <div className="audit-next-action">
          <strong>Что делать сейчас</strong>
          <span>{result.next}</span>
        </div>
      </div>

      <div className="audit-automation-grid" aria-label="Что уже автоматизировано">
        <article className={`audit-agent-card audit-agent-${agentTone(audit.security_agent.status)}`}>
          <div>
            <strong>Агент проверки</strong>
            <span>{audit.security_agent.status_label}</span>
          </div>
          <dl>
            <div>
              <dt>Модель</dt>
              <dd>{audit.security_agent.model}</dd>
            </div>
            <div>
              <dt>Провайдер</dt>
              <dd>{audit.security_agent.provider}</dd>
            </div>
            <div>
              <dt>Резервный режим</dt>
              <dd>{audit.security_agent.fallback}</dd>
            </div>
          </dl>
          <p>{audit.security_agent.explanation}</p>
        </article>
        {rows.map((row) => (
          <article key={row.label} className={`audit-automation-row audit-automation-${row.state}`}>
            {row.state === "done" ? <CheckCircle2 aria-hidden="true" size={17} /> : <AlertTriangle aria-hidden="true" size={17} />}
            <div>
              <strong>{row.label}</strong>
              <span>{row.value}</span>
            </div>
          </article>
        ))}
      </div>

      <div className="audit-blockers">
        <div>
          <ClipboardList aria-hidden="true" size={18} />
          <strong>Почему это ещё не готовый report</strong>
        </div>
        {blockers.length ? (
          <ul>
            {blockers.map((item) => <li key={item}>{item}</li>)}
          </ul>
        ) : (
          <p>Критичных блокеров для приватного report wr3 не видит, но human review всё равно обязателен.</p>
        )}
      </div>

      <div className="audit-workflow-hint">
        <FileSearch aria-hidden="true" size={18} />
        <span>
          Рабочая логика: скан создаёт кандидата → очередь багов помогает проверить evidence → только после подтверждения
          создаётся disclosure case. wr3 не отправляет письма автоматически.
        </span>
      </div>
    </section>
  );
}
