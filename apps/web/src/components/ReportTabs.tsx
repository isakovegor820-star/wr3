"use client";

import { useState } from "react";
import type { AuditSummary, Finding } from "@wr3/shared";
import { LockKeyhole } from "lucide-react";
import { tCap } from "@/lib/i18n";
import { FindingsList } from "./FindingsList";

type Tab = "findings" | "score" | "raw";

export function ReportTabs({ audit, findings }: { audit: AuditSummary; findings: Finding[] }) {
  const [tab, setTab] = useState<Tab>("findings");

  return (
    <section className="panel">
      <div className="tabs" role="tablist" aria-label="Разделы отчёта">
        <button type="button" className={tab === "findings" ? "tab tab-active" : "tab"} onClick={() => setTab("findings")}>
          Находки
        </button>
        <button type="button" className={tab === "score" ? "tab tab-active" : "tab"} onClick={() => setTab("score")}>
          Разбор оценки
        </button>
        <button type="button" className={tab === "raw" ? "tab tab-active" : "tab"} onClick={() => setTab("raw")}>
          Сырые выводы
        </button>
      </div>

      {tab === "findings" ? (
        <>
          <div className="section-heading">
            <div>
              <p className="eyebrow">Находки</p>
              <h2>Приоритизированные риски</h2>
            </div>
            <span>{findings.length} шт.</span>
          </div>
          <FindingsList findings={findings} />
        </>
      ) : null}

      {tab === "score" ? (
        <div className="score-tab">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Оценка риска</p>
              <h2>Прозрачный разбор по пяти осям</h2>
            </div>
          </div>
          {audit.score ? (
            <dl className="score-definition-list">
              <div>
                <dt>Безопасность кода</dt>
                <dd>{audit.score.code_security_score} · 35%</dd>
              </div>
              <div>
                <dt>Токеномика / централизация</dt>
                <dd>{audit.score.centralization_score} · 20%</dd>
              </div>
              <div>
                <dt>Риск ликвидности</dt>
                <dd>{audit.score.liquidity_score} · 15%</dd>
              </div>
              <div>
                <dt>Команда / KYC</dt>
                <dd>{audit.score.team_kyc_score} · 15%</dd>
              </div>
              <div>
                <dt>Поведение в сети</dt>
                <dd>{audit.score.behavior_score} · 15%</dd>
              </div>
              <div>
                <dt>Ограничения</dt>
                <dd>{audit.score.caps_applied.map(tCap).join(", ") || "нет"}</dd>
              </div>
              <div>
                <dt>Источник кода</dt>
                <dd>{audit.source_metadata.bytecode_only ? "ограниченный bytecode-режим" : audit.source_metadata.source_origin}</dd>
              </div>
              <div>
                <dt>Прокси</dt>
                <dd>{audit.source_metadata.proxy_info.is_proxy ? audit.source_metadata.proxy_info.proxy_type || "обнаружен" : "не обнаружен"}</dd>
              </div>
            </dl>
          ) : (
            <p className="empty-state">Оценка ещё считается.</p>
          )}
        </div>
      ) : null}

      {tab === "raw" ? (
        <div className="raw-gated">
          <LockKeyhole aria-hidden="true" size={24} />
          <div>
            <p className="eyebrow">{audit.access.is_owner ? "Владелец подтверждён" : "Доступ закрыт"}</p>
            <h2>
              {audit.access.can_view_raw_outputs
                ? "Владелец может запросить сырые метаданные."
                : "Сырые выводы движков требуют платный доступ владельца."}
            </h2>
            <p>
              В MVP этот блок намеренно показывает только метаданные. Приватный исходный код,
              находки, PoC-трейсы и сырой вывод инструментов должны оставаться зашифрованными и закрытыми для владельца.
            </p>
          </div>
        </div>
      ) : null}
    </section>
  );
}
