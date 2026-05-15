import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { ReportTabs } from "@/components/ReportTabs";
import { ScorePanel } from "@/components/ScorePanel";
import { StageTimeline } from "@/components/StageTimeline";
import { StatusRefresher } from "@/components/StatusRefresher";
import { demoAudit, demoFindings } from "@/lib/demo";
import { getAudit, getFindings } from "@/lib/api";
import { auditStateLabels, chainLabels, tLimitation } from "@/lib/i18n";
import type { AuditSummary, Finding } from "@wr3/shared";

async function loadAudit(
  id: string,
  ownerToken?: string,
): Promise<{ audit: AuditSummary; findings: Finding[]; error: string | null }> {
  if (id === "demo") {
    return { audit: demoAudit, findings: demoFindings, error: null };
  }
  try {
    const [audit, findings] = await Promise.all([getAudit(id, ownerToken), getFindings(id, ownerToken)]);
    return { audit, findings, error: null };
  } catch (err) {
      return {
      audit: demoAudit,
      findings: demoFindings,
      error: err instanceof Error ? err.message : "Не удалось загрузить аудит"
    };
  }
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

      {error ? <p className="error-box">API недоступен, показываю демо-данные. {error}</p> : null}

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

      <StageTimeline state={audit.state} failedStages={audit.failed_stages} limitations={audit.limitations} />
      <ScorePanel score={audit.score} />
      <section className="panel access-panel">
        <div>
          <p className="eyebrow">Доступ</p>
          <h2>{audit.access.is_owner ? "Доступ владельца подтверждён" : "Публичный или редактированный режим"}</h2>
        </div>
        <p>
          {audit.access.can_view_private_findings
            ? "Приватные находки видны в этой MVP-сессии. Сырые PoC-артефакты всё равно закрыты по тарифу."
            : "Приватные находки и PoC-артефакты скрыты без токена владельца или авторизованного владельца."}
        </p>
      </section>

      <ReportTabs audit={audit} findings={findings} />

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
