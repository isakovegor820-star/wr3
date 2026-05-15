import Link from "next/link";
import { ArrowLeft, CheckCircle2, CircleDashed, PlugZap } from "lucide-react";
import { getIntegrationStatus } from "@/lib/api";
import { tStatus } from "@/lib/i18n";

const categoryLabels: Record<string, string> = {
  audit_ingestion: "Загрузка исходников",
  onchain_reads: "Чтение блокчейна",
  llm_triage: "ИИ-триаж",
  rag: "База знаний",
  telegram: "Telegram",
  billing: "Биллинг",
  telegram_payments: "Платежи в Telegram",
  monitoring: "Мониторинг",
  observability: "Наблюдаемость",
  solana: "Solana beta",
  roadmap: "План развития",
  notifications: "Уведомления"
};

export default async function IntegrationsPage() {
  const status = await getIntegrationStatus();
  const grouped = status.integrations.reduce<Record<string, typeof status.integrations>>((acc, integration) => {
    acc[integration.category] = [...(acc[integration.category] ?? []), integration];
    return acc;
  }, {});

  return (
    <main className="audit-shell">
      <nav className="top-nav">
        <Link href="/">
          <ArrowLeft aria-hidden="true" size={17} />
          На главную
        </Link>
      </nav>

      <header className="audit-header">
        <div>
          <p className="eyebrow">Готовность бесплатных API</p>
          <h1>Статус API-интеграций wr3</h1>
          <p>
            Здесь видно, какие внешние API реально подключены, где работает бесплатный резерв,
            а где нужен ключ или внешний доступ.
          </p>
        </div>
        <div className="progress-pill">
          {status.counts.configured + status.counts.free_fallback}/{status.integrations.length}
        </div>
      </header>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">RPC</p>
          <h2>Бесплатные публичные RPC-резервы</h2>
          </div>
        </div>
        <div className="compact-definition-list">
          {status.rpc.map((rpc) => (
            <div key={rpc.chain}>
              <dt>{rpc.chain}</dt>
              <dd>{rpc.url_host ?? "нет"} · {rpc.source}</dd>
            </div>
          ))}
        </div>
      </section>

      {Object.entries(grouped).map(([category, integrations]) => (
        <section className="panel" key={category}>
          <div className="section-heading">
            <div>
              <p className="eyebrow">{categoryLabels[category] ?? category}</p>
              <h2>{categoryLabels[category] ?? category}</h2>
            </div>
          </div>
          <div className="tool-grid">
            {integrations.map((integration) => (
              <article className="tool-card" key={integration.id}>
                <div className="tool-card-header">
                  {integration.status === "configured" || integration.status === "free_fallback" || integration.status === "manual" ? (
                    <CheckCircle2 aria-hidden="true" size={20} />
                  ) : (
                    <CircleDashed aria-hidden="true" size={20} />
                  )}
                  <div>
                    <h3>{integration.label}</h3>
                    <p>{integration.priority} · {tStatus(integration.status)}</p>
                  </div>
                </div>
                <p className="muted-copy">{integration.free_mode}</p>
                <div className="tool-install">
                  <PlugZap aria-hidden="true" size={17} />
                  <span>{integration.env_vars.join(", ")}</span>
                </div>
                <p className="muted-copy">{integration.next_step}</p>
              </article>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
