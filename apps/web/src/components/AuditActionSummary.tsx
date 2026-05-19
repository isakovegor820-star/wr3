import type { AuditSummary, Finding } from "@wr3/shared";
import { AlertTriangle, BellRing, CheckCircle2, ClipboardList, ShieldCheck, XCircle } from "lucide-react";
import { chainLabels, severityLabels, tFindingText, tLimitation } from "@/lib/i18n";

const severityRank: Record<Finding["severity"], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4
};

function sortedFindings(findings: Finding[]) {
  return [...findings].sort(
    (left, right) => severityRank[left.severity] - severityRank[right.severity] || right.confidence - left.confidence
  );
}

function unique(items: string[]) {
  return [...new Set(items.filter(Boolean))];
}

function buildSafeDraft(audit: AuditSummary, finding: Finding | null, readyCount: number) {
  const target = audit.address ?? "контракт / исходный код";
  if (finding && readyCount > 0) {
    return `Тема: responsible disclosure report для ${chainLabels[audit.chain]} ${target}

Здравствуйте.

Мы пишем приватно в рамках responsible disclosure. wr3 отметил security-находку, которую можно передать на проверку вашей security-команде.

Кратко:
- Сеть: ${chainLabels[audit.chain]}
- Цель: ${target}
- Severity: ${severityLabels[finding.severity]}
- Находка: ${tFindingText(finding.summary)}
- Готовность: ${finding.disclosure_assessment.readiness_label}

Безопасность:
- Mainnet-транзакции не отправлялись.
- Средства не перемещались.
- Публичных обвинений не публиковалось.
- Детали и PoC готовы передавать только приватно в официальный security contact.

Просим подтвердить, что этот канал подходит для security disclosure, или направить нас на правильный security/bounty contact.`;
  }

  return `Тема: уточнение security contact / bounty scope для ${chainLabels[audit.chain]} ${target}

Здравствуйте.

Мы проводим пассивную проверку security-сигналов и хотим уточнить правильный канал для responsible disclosure.

По текущей цели у нас пока нет подтверждённого bug report, поэтому мы не отправляем технические детали и не делаем публичных заявлений.

Цель:
- Сеть: ${chainLabels[audit.chain]}
- Контракт / адрес: ${target}

Подскажите, пожалуйста, официальный security contact или bug bounty scope для этой цели.

С уважением,
wr3 research`;
}

export function AuditActionSummary({ audit, findings }: { audit: AuditSummary; findings: Finding[] }) {
  const ordered = sortedFindings(findings);
  const ready = ordered.filter((finding) => finding.disclosure_assessment.can_contact_support);
  const candidates = ordered.filter((finding) => finding.disclosure_assessment.verdict === "too_early");
  const dismissed = ordered.filter((finding) => finding.disclosure_assessment.verdict === "do_not_write");
  const primary = ready[0] ?? candidates[0] ?? ordered[0] ?? null;
  const evidenceGaps = unique(ordered.flatMap((finding) => finding.disclosure_assessment.evidence_gaps)).slice(0, 6);
  const blockerLimitations = audit.limitations
    .filter((item) => item.includes("llm_triage") || item.includes("poc") || item.includes("fuzzing") || item.includes("zdr"))
    .map(tLimitation)
    .slice(0, 4);
  const blockers = unique([...evidenceGaps, ...blockerLimitations]).slice(0, 7);
  const draft = buildSafeDraft(audit, primary, ready.length);

  const state =
    ready.length > 0
      ? {
          className: "ready",
          icon: CheckCircle2,
          title: `Можно писать по ${ready.length} наход${ready.length === 1 ? "ке" : "кам"}`,
          subtitle: "Есть достаточно сильный сигнал для приватного responsible disclosure.",
          decision: "Писать только приватно в официальный security contact."
        }
      : candidates.length > 0
        ? {
            className: "blocked",
            icon: AlertTriangle,
            title: "Готовых багов для поддержки нет",
            subtitle: `wr3 нашёл ${candidates.length} кандидат${candidates.length === 1 ? "" : "а"}, но доказательств пока не хватает.`,
            decision: "Не отправлять как bug report. Сначала довести кандидата до проверки."
          }
        : {
            className: "quiet",
            icon: ShieldCheck,
            title: "Багов для обращения не найдено",
            subtitle: "Этот проход не дал actionable находок.",
            decision: "Можно оставить адрес в мониторинге и продолжить поиск по другим целям."
          };

  const Icon = state.icon;

  return (
    <section className={`panel audit-action-summary audit-action-${state.className}`}>
      <div className="audit-action-hero">
        <div>
          <p className="eyebrow">Точный итог</p>
          <h2>
            <Icon aria-hidden="true" size={24} />
            {state.title}
          </h2>
          <p>{state.subtitle}</p>
        </div>
        <div className="audit-action-decision">
          <strong>Что делать</strong>
          <span>{state.decision}</span>
        </div>
      </div>

      <div className="audit-action-grid">
        <article>
          <span className="metric-label">Готово к письму</span>
          <strong>{ready.length}</strong>
          <small>только private disclosure</small>
        </article>
        <article>
          <span className="metric-label">Кандидаты</span>
          <strong>{candidates.length}</strong>
          <small>нужна проверка</small>
        </article>
        <article>
          <span className="metric-label">Не писать</span>
          <strong>{dismissed.length}</strong>
          <small>false-positive / отклонено</small>
        </article>
        <article>
          <span className="metric-label">Оценка</span>
          <strong>{audit.score?.final_score ?? "..."}</strong>
          <small>risk score</small>
        </article>
      </div>

      {primary ? (
        <div className="audit-primary-target">
          <div>
            <p className="eyebrow">Главный сигнал</p>
            <h3>{tFindingText(primary.summary)}</h3>
            <p>
              {severityLabels[primary.severity]} · уверенность {Math.round(primary.confidence * 100)}% ·{" "}
              {primary.disclosure_assessment.location_label}
            </p>
          </div>
          <span className={`finding-verdict-chip finding-verdict-${primary.disclosure_assessment.verdict}`}>
            {primary.disclosure_assessment.verdict_label}
          </span>
        </div>
      ) : null}

      <div className="audit-action-columns">
        <article className="audit-next-checks">
          <div className="audit-mini-heading">
            <ClipboardList aria-hidden="true" size={18} />
            <strong>Почему пока могут послать</strong>
          </div>
          {blockers.length ? (
            <ul>
              {blockers.map((item) => <li key={item}>{item}</li>)}
            </ul>
          ) : (
            <p>Критичных блокеров wr3 не видит, но ручная проверка всё равно обязательна.</p>
          )}
        </article>

        <article className="audit-next-checks">
          <div className="audit-mini-heading">
            <CheckCircle2 aria-hidden="true" size={18} />
            <strong>Как довести до результата</strong>
          </div>
          <ol>
            <li>Найти точную функцию/строку или подтвердить вручную участок кода.</li>
            <li>Получить подтверждение от Aderyn/Wake/Slither или ручного AST-review.</li>
            <li>Добиться успешного ИИ-триажа: Claude Opus сейчас выбран, но нужен доступ к модели.</li>
            <li>Подтвердить безопасно: local/fork/test, без mainnet-действий.</li>
            <li>После этого отправлять только приватный responsible disclosure.</li>
          </ol>
        </article>
      </div>

      <div className="audit-draft-grid">
        <article className="audit-support-draft">
          <div className="audit-mini-heading">
            {ready.length > 0 ? <CheckCircle2 aria-hidden="true" size={18} /> : <XCircle aria-hidden="true" size={18} />}
            <strong>{ready.length > 0 ? "Черновик письма" : "Что можно писать сейчас"}</strong>
          </div>
          <pre>{draft}</pre>
        </article>

        <article className="audit-monitoring-card">
          <div className="audit-mini-heading">
            <BellRing aria-hidden="true" size={18} />
            <strong>24/7 режим</strong>
          </div>
          <p>
            Этот экран показывает результат одного скана. Для настоящего “ищет само 24/7” цель должна попасть в watchlist:
            wr3 будет периодически пересканировать адрес, поднимать кандидатов в очередь и готовить черновик обращения.
          </p>
          <p className="muted-copy">
            Важно: даже в 24/7 режиме wr3 не должен автоматически отправлять exploit/PoC. Сначала ручная проверка и scope.
          </p>
        </article>
      </div>
    </section>
  );
}
