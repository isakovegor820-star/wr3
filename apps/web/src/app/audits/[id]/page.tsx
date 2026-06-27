import Link from "next/link";
import { AlertTriangle, ArrowLeft, CheckCircle2, ExternalLink, FileSearch, ShieldCheck, XCircle } from "lucide-react";
import { AuditActionSummary } from "@/components/AuditActionSummary";
import { AuditInterpretationPanel } from "@/components/AuditInterpretationPanel";
import { ReportTabs } from "@/components/ReportTabs";
import { ScorePanel } from "@/components/ScorePanel";
import { StageTimeline } from "@/components/StageTimeline";
import { StatusRefresher } from "@/components/StatusRefresher";
import { demoAudit, demoFindings } from "@/lib/demo";
import { getAudit, getFindings } from "@/lib/api";
import { auditStateLabels, chainLabels, tLimitation, tStatus } from "@/lib/i18n";
import type { AuditSummary, Finding } from "@wr3/shared";

async function loadAudit(
  id: string,
  ownerToken?: string,
): Promise<{ audit: AuditSummary | null; findings: Finding[]; error: string | null }> {
  if (id === "demo") {
    return { audit: demoAudit, findings: demoFindings, error: null };
  }
  try {
    const [audit, findings] = await Promise.all([getAudit(id, ownerToken), getFindings(id, ownerToken)]);
    return { audit, findings, error: null };
  } catch (err) {
    return {
      audit: null,
      findings: [],
      error: err instanceof Error ? err.message : "Не удалось загрузить аудит"
    };
  }
}

const severityRank: Record<Finding["severity"], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4
};

function sortFindings(findings: Finding[]) {
  return [...findings].sort(
    (left, right) => severityRank[left.severity] - severityRank[right.severity] || right.confidence - left.confidence
  );
}

function sourceSignal(audit: AuditSummary) {
  if (audit.source_metadata.bytecode_only || audit.state === "needs_source") {
    return {
      tone: "warning",
      label: "Source не найден",
      detail: "Скан ограничен: без verified source нельзя уверенно доказать большинство source-level багов."
    };
  }
  if (audit.source_metadata.source_origin === "unknown" && !audit.source_metadata.source_hash) {
    return {
      tone: "warning",
      label: "Source не определён",
      detail: "Платформа не видит источник кода. Нужен адрес с verified source или вставленный код."
    };
  }
  return {
    tone: "ready",
    label: "Source найден",
    detail:
      audit.source_metadata.source_origin === "pasted"
        ? "Код вставлен пользователем и доступен статическим движкам."
        : `Источник: ${audit.source_metadata.source_origin}.`
  };
}

function verificationCounts(findings: Finding[]) {
  const confirmed = findings.filter(
    (finding) => finding.evidence.poc_status === "confirmed" || finding.exploitability === "confirmed"
  );
  const dismissed = findings.filter(
    (finding) => finding.exploitability === "dismissed" || finding.disclosure_assessment.verdict === "do_not_write"
  );
  const candidates = findings.filter((finding) => !confirmed.includes(finding) && !dismissed.includes(finding));
  return { confirmed: confirmed.length, candidates: candidates.length, dismissed: dismissed.length };
}

function safeNextStep(audit: AuditSummary, findings: Finding[]) {
  const ordered = sortFindings(findings);
  const primary =
    ordered.find((finding) => finding.disclosure_assessment.can_contact_support) ??
    ordered.find((finding) => finding.disclosure_assessment.verdict === "too_early") ??
    ordered[0];
  if (primary?.disclosure_assessment.next_step) {
    return primary.disclosure_assessment.next_step;
  }
  if (audit.state === "needs_source" || audit.source_metadata.bytecode_only) {
    return "Добавить verified source или вставить исходный код, затем повторить статический анализ.";
  }
  if (audit.static_analysis_status === "failed") {
    return "Починить локальные static tools и повторить скан; без этого результат нельзя считать полным.";
  }
  return "Оставить цель в мониторинге или запустить deep scan, если контракт критичен.";
}

function SourceStatusPanel({ audit, findings }: { audit: AuditSummary; findings: Finding[] }) {
  const source = sourceSignal(audit);
  const counts = verificationCounts(findings);
  const SourceIcon = source.tone === "ready" ? CheckCircle2 : AlertTriangle;

  return (
    <section className="panel source-status-panel">
      <div className="source-status-head">
        <div>
          <p className="eyebrow">Результат автономного прохода</p>
          <h2>От входа до безопасного next step</h2>
        </div>
        <span className={`status-chip status-chip-${source.tone}`}>
          <SourceIcon aria-hidden="true" size={16} />
          {source.label}
        </span>
      </div>
      <div className="source-status-grid">
        <article>
          <FileSearch aria-hidden="true" size={18} />
          <span>Источник</span>
          <strong>{source.label}</strong>
          <small>{source.detail}</small>
        </article>
        <article>
          <ShieldCheck aria-hidden="true" size={18} />
          <span>Static layer</span>
          <strong>{tStatus(audit.static_analysis_status)}</strong>
          <small>Ошибки отдельных движков видны во вкладке raw metadata.</small>
        </article>
        <article>
          <FileSearch aria-hidden="true" size={18} />
          <span>Raw findings</span>
          <strong>{findings.length}</strong>
          <small>Нормализованные сигналы; сырой вывод хранится как приватный artifact.</small>
        </article>
        <article>
          <CheckCircle2 aria-hidden="true" size={18} />
          <span>Подтверждено</span>
          <strong>{counts.confirmed}</strong>
          <small>PoC/fork/test или exploitability=confirmed.</small>
        </article>
        <article>
          <AlertTriangle aria-hidden="true" size={18} />
          <span>Кандидаты</span>
          <strong>{counts.candidates}</strong>
          <small>Есть сигнал, но не хватает доказательств.</small>
        </article>
        <article>
          <XCircle aria-hidden="true" size={18} />
          <span>Не писать</span>
          <strong>{counts.dismissed}</strong>
          <small>False positive, слабый сигнал или небезопасно отправлять report.</small>
        </article>
      </div>
      <div className="source-next-step">
        <strong>Безопасный следующий шаг</strong>
        <span>{safeNextStep(audit, findings)}</span>
      </div>
    </section>
  );
}

export default async function AuditPage({
  params,
  searchParams
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ owner_token?: string }>;
}) {
  const { id } = await params;
  const { owner_token: ownerToken } = await searchParams;
  const { audit, findings, error } = await loadAudit(id, ownerToken);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  const reportHref =
    id === "demo"
      ? "#"
      : `${apiBase}/v1/audits/${id}/report${ownerToken ? `?owner_token=${encodeURIComponent(ownerToken)}` : ""}`;

  if (!audit) {
    return (
      <main className="audit-shell">
        <nav className="top-nav">
          <Link href="/">
            <ArrowLeft aria-hidden="true" size={17} />
            Новый скан
          </Link>
        </nav>
        <section className="panel audit-load-error">
          <AlertTriangle aria-hidden="true" size={24} />
          <div>
            <p className="eyebrow">Отчёт не загружен</p>
            <h1>Платформа не получила результат аудита</h1>
            <p>
              Нельзя показывать демо-данные вместо реального security-результата. Проверь API, токен владельца или ID аудита и повтори запрос.
            </p>
            {error ? <p className="error-box">{error}</p> : null}
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="audit-shell">
      <StatusRefresher state={audit.state} />
      <nav className="top-nav">
        <Link href="/">
          <ArrowLeft aria-hidden="true" size={17} />
          Новый скан
        </Link>
        <a href={reportHref} aria-disabled={id === "demo"}>
          <ExternalLink aria-hidden="true" size={17} />
          Markdown-отчёт
        </a>
      </nav>

      <header className="audit-header">
        <div>
          <p className="eyebrow">Отчёт аудита</p>
          <h1>{chainLabels[audit.chain]}: отчёт предаудита</h1>
          <p className="audit-address">{audit.address ?? "только исходный код"}</p>
          <p>
            {audit.engine_version} · {audit.score_version} · {auditStateLabels[audit.state]}
          </p>
        </div>
        <div className="progress-pill">{audit.progress}%</div>
      </header>

      <SourceStatusPanel audit={audit} findings={findings} />

      <StageTimeline
        state={audit.state}
        failedStages={audit.failed_stages}
        limitations={audit.limitations}
        staticAnalysisStatus={audit.static_analysis_status}
      />
      <AuditActionSummary audit={audit} findings={findings} />
      <AuditInterpretationPanel audit={audit} findings={findings} />
      <ScorePanel score={audit.score} />
      <section className="panel access-panel">
        <div>
          <p className="eyebrow">Доступ</p>
          <h2>{audit.access.is_owner ? "Доступ владельца подтверждён" : "Публичный или редактированный режим"}</h2>
        </div>
        <p>
          {audit.access.can_view_private_findings
            ? "Приватные находки видны в этой MVP-сессии. Сырые PoC-артефакты доступны владельцу как приватные артефакты."
            : "Приватные находки и PoC-артефакты скрыты без токена владельца или авторизованного владельца."}
        </p>
      </section>

      <ReportTabs audit={audit} findings={findings} ownerToken={ownerToken} />

      <section className="panel limitations-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Область проверки</p>
            <h2>Ограничения и защитные ворота</h2>
          </div>
        </div>
        <ul>
          {audit.limitations.map((limitation) => (
            <li key={limitation}>{tLimitation(limitation)}</li>
          ))}
          {audit.adversarial_input_detected ? <li>В исходном коде обнаружены признаки prompt-injection.</li> : null}
        </ul>
      </section>
    </main>
  );
}
