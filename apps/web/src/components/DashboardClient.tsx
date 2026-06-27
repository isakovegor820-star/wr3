"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Filter, RefreshCw, RotateCcw, Trash2 } from "lucide-react";
import type { AuditState, Chain, Severity } from "@wr3/shared";
import { deleteAudit, listAudits, retryAudit, type DashboardAudit } from "@/lib/api";
import { auditStateLabels, chainLabels, severityLabels } from "@/lib/i18n";

const chains: Array<Chain | ""> = ["", "ethereum", "base", "bsc", "arbitrum", "solana"];
const states: Array<AuditState | ""> = [
  "",
  "queued",
  "needs_source",
  "completed",
  "partial",
  "failed",
  "poc_running",
  "fuzzing_running"
];
const severities: Array<Severity | ""> = ["", "critical", "high", "medium", "low", "info"];

export function DashboardClient() {
  const [chain, setChain] = useState<Chain | "">("");
  const [state, setState] = useState<AuditState | "">("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [audits, setAudits] = useState<DashboardAudit[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyAudit, setBusyAudit] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      setAudits(await listAudits({ chain, state, severity }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Панель аудитов не загрузилась");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [chain, state, severity]);

  const grouped = useMemo(() => {
    const map = new Map<string, DashboardAudit[]>();
    for (const audit of audits) {
      const list = map.get(audit.project_key) ?? [];
      list.push(audit);
      map.set(audit.project_key, list);
    }
    return Array.from(map.entries());
  }, [audits]);

  async function runRetry(audit: DashboardAudit) {
    setBusyAudit(audit.audit_id);
    try {
      await retryAudit(audit.audit_id, audit.owner_access_token ?? undefined);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Повтор не запустился");
    } finally {
      setBusyAudit(null);
    }
  }

  async function runDelete(audit: DashboardAudit) {
    setBusyAudit(audit.audit_id);
    try {
      await deleteAudit(audit.audit_id, audit.owner_access_token ?? undefined);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Удаление не сработало");
    } finally {
      setBusyAudit(null);
    }
  }

  return (
    <section className="panel dashboard-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Локальная панель</p>
          <h2>Аудиты из локальной базы</h2>
        </div>
        <button type="button" className="secondary-button" onClick={load}>
          <RefreshCw aria-hidden="true" size={17} />
          Обновить
        </button>
      </div>

      <div className="filter-bar" aria-label="Фильтры панели аудитов">
        <Filter aria-hidden="true" size={18} />
        <label>
          Сеть
          <select value={chain} onChange={(event) => setChain(event.target.value as Chain | "")}>
            {chains.map((item) => (
              <option key={item || "all"} value={item}>
                {item ? chainLabels[item] : "Все сети"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Состояние
          <select value={state} onChange={(event) => setState(event.target.value as AuditState | "")}>
            {states.map((item) => (
              <option key={item || "all"} value={item}>
                {item ? auditStateLabels[item] : "Все состояния"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Важность
          <select value={severity} onChange={(event) => setSeverity(event.target.value as Severity | "")}>
            {severities.map((item) => (
              <option key={item || "all"} value={item}>
                {item ? severityLabels[item] : "Любая"}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? <p className="error-box">{error}</p> : null}
      {isLoading ? <p className="empty-state">Загружаю локальные аудиты...</p> : null}
      {!isLoading && grouped.length === 0 ? <p className="empty-state">Аудитов под эти фильтры пока нет.</p> : null}

      <div className="dashboard-groups">
        {grouped.map(([projectKey, projectAudits]) => (
          <article className="dashboard-group" key={projectKey}>
            <div className="dashboard-group-header">
              <h3>{projectKey}</h3>
              <span>{projectAudits.length} ауд.</span>
            </div>
            <div className="dashboard-list">
              {projectAudits.map((audit) => {
                const href = `/audits/${audit.audit_id}${
                  audit.owner_access_token ? `?owner_token=${encodeURIComponent(audit.owner_access_token)}` : ""
                }`;
                return (
                  <div className="dashboard-row" key={audit.audit_id}>
                    <div>
                      <Link href={href} className="artifact-link">
                        {audit.audit_id}
                      </Link>
                      <p className="muted-copy">
                        {chainLabels[audit.chain]} · {auditStateLabels[audit.state]} ·{" "}
                        {audit.finding_count} находок
                      </p>
                    </div>
                    <div className="dashboard-metrics">
                      <span>{audit.score?.final_score ?? "--"}</span>
                      <span>{audit.highest_severity ? severityLabels[audit.highest_severity] : "нет"}</span>
                    </div>
                    <div className="dashboard-actions">
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={busyAudit === audit.audit_id}
                        onClick={() => runRetry(audit)}
                      >
                        <RotateCcw aria-hidden="true" size={16} />
                        Повторить
                      </button>
                      <button
                        type="button"
                        className="secondary-button danger-button"
                        disabled={busyAudit === audit.audit_id}
                        onClick={() => runDelete(audit)}
                      >
                        <Trash2 aria-hidden="true" size={16} />
                        Удалить
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
