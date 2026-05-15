import Link from "next/link";
import { ArrowLeft, CheckCircle2, CircleDashed, Terminal } from "lucide-react";
import { getToolsStatus } from "@/lib/api";
import { tStatus } from "@/lib/i18n";

const categoryLabels: Record<string, string> = {
  static: "Статический анализ",
  poc: "Локальный PoC",
  fuzzing: "Локальный фаззинг",
  solana: "Solana beta"
};

export default async function ToolsStatusPage() {
  const status = await getToolsStatus();
  const grouped = status.tools.reduce<Record<string, typeof status.tools>>((acc, tool) => {
    acc[tool.category] = [...(acc[tool.category] ?? []), tool];
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
          <p className="eyebrow">Готовность localhost</p>
          <h1>Статус локальных инструментов аудита</h1>
          <p>
            Отсутствующие инструменты не ломают pipeline: wr3 создаёт артефакт со статусом «пропущено»
            и показывает понятную причину. Установка нужна для полноценного PoC, фаззинга и статического анализа.
          </p>
        </div>
        <div className="progress-pill">
          {status.required_installed}/{status.required_total}
        </div>
      </header>

      <section className="panel access-panel">
        <div>
          <p className="eyebrow">Итог</p>
          <h2>{status.status === "ready" ? "Все обязательные инструменты найдены" : "Часть инструментов пока отсутствует"}</h2>
        </div>
        <p>
          Установлено всего: {status.installed_total}. Необязательных отсутствует: {status.optional_missing.length}.
          Обязательных отсутствует: {status.missing_required.length}.
        </p>
      </section>

      {Object.entries(grouped).map(([category, tools]) => (
        <section className="panel" key={category}>
          <div className="section-heading">
            <div>
              <p className="eyebrow">{categoryLabels[category] ?? category}</p>
              <h2>{categoryLabels[category] ?? category}</h2>
            </div>
          </div>
          <div className="tool-grid">
            {tools.map((tool) => (
              <article className="tool-card" key={tool.id}>
                <div className="tool-card-header">
                  {tool.installed ? (
                    <CheckCircle2 aria-hidden="true" size={20} />
                  ) : (
                    <CircleDashed aria-hidden="true" size={20} />
                  )}
                  <div>
                    <h3>{tool.label}</h3>
                    <p>{tool.binary}</p>
                  </div>
                </div>
                <dl className="compact-definition-list">
                  <div>
                    <dt>Статус</dt>
                    <dd>{tool.installed ? "установлено" : tStatus(tool.status)}</dd>
                  </div>
                  <div>
                    <dt>Версия</dt>
                    <dd>{tool.version}</dd>
                  </div>
                  <div>
                    <dt>Путь</dt>
                    <dd>{tool.path ?? "не найден"}</dd>
                  </div>
                  <div>
                    <dt>Обязательный</dt>
                    <dd>{tool.required_for_local_100 ? "да" : "необязательный"}</dd>
                  </div>
                </dl>
                <div className="tool-install">
                  <Terminal aria-hidden="true" size={17} />
                  <span>{tool.install_hint}</span>
                </div>
                <p className="muted-copy">{tool.safe_scope}</p>
              </article>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
