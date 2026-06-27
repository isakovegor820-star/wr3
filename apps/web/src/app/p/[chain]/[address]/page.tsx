import Link from "next/link";
import { ArrowLeft, ShieldCheck, ShieldX } from "lucide-react";
import { FindingsList } from "@/components/FindingsList";
import { RiskBadge } from "@/components/RiskBadge";
import { getPublicProject } from "@/lib/api";
import { chainLabels, tLimitation } from "@/lib/i18n";
import type { Chain } from "@wr3/shared";

export default async function PublicProjectPage({
  params
}: {
  params: Promise<{ chain: Chain; address: string }>;
}) {
  const { chain, address } = await params;
  let project: Awaited<ReturnType<typeof getPublicProject>>;
  try {
    project = await getPublicProject(chain, address);
  } catch {
    return (
      <main className="audit-shell">
        <nav className="top-nav">
          <Link href="/">
            <ArrowLeft aria-hidden="true" size={17} />
            Новый скан
          </Link>
        </nav>
        <header className="audit-header">
          <div>
            <p className="eyebrow">Публичная страница проекта</p>
            <h1>{chainLabels[chain] ?? chain}: карточка недоступна</h1>
            <p className="audit-address">{address}</p>
          </div>
        </header>
        <section className="panel">
          <p>
            Не удалось загрузить публичную карточку. Возможно, этот адрес ещё не сканировался,
            адрес введён неверно, или API сейчас недоступен.
          </p>
        </section>
      </main>
    );
  }
  const score = project.score?.final_score ?? null;
  const HarborIcon = project.safe_harbor_status ? ShieldCheck : ShieldX;

  return (
    <main className="audit-shell">
      <nav className="top-nav">
        <Link href="/">
          <ArrowLeft aria-hidden="true" size={17} />
          Новый скан
        </Link>
      </nav>

      <header className="audit-header">
        <div>
          <p className="eyebrow">Публичная страница проекта</p>
          <h1>{chainLabels[chain]}: сводка риска</h1>
          <p className="audit-address">{address}</p>
          <p>Публичный режим скрывает приватные находки и PoC-артефакты.</p>
        </div>
        <div className="progress-pill">{score ?? "--"}</div>
      </header>

      <section className="panel public-score-panel">
        <div>
          <p className="eyebrow">Оценка риска</p>
          {score === null ? <h2>Публичной wr3-оценки пока нет</h2> : <RiskBadge score={score} />}
        </div>
        <div className="safe-harbor-signal">
          <HarborIcon aria-hidden="true" size={21} />
          <span>{project.safe_harbor_status ? "Есть в Safe Harbor" : "Нет в Safe Harbor"}</span>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Публичные находки</p>
            <h2>Публичные элементы без приватных деталей</h2>
          </div>
          <span>{project.public_findings.length} шт.</span>
        </div>
        <FindingsList findings={project.public_findings} />
      </section>

      <section className="panel limitations-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Ограничения</p>
            <h2>Публичные ограничения безопасности</h2>
          </div>
        </div>
        <ul>
          {project.limitations.map((limitation) => (
            <li key={limitation}>{tLimitation(limitation)}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
