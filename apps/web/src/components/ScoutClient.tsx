"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, ExternalLink, Loader2, Play, Power, Radar, RefreshCw, ShieldCheck, Square } from "lucide-react";
import type { Chain } from "@wr3/shared";
import { chainLabels } from "@/lib/i18n";
import {
  discoverScoutTargets,
  getScoutAutopilotStatus,
  getScoutReviewQueue,
  runScoutAutopilotNow,
  runScoutAllNetworks,
  runScoutOnce,
  startScoutAutopilot,
  stopScoutAutopilot,
  type ScoutAutopilotStatus,
  type ScoutQueuedAudit,
  type ScoutReviewItem,
  type ScoutReviewQueue,
  type ScoutTarget
} from "@/lib/api";

const scoutChains: { value: Chain | ""; label: string }[] = [
  { value: "", label: "Все" },
  { value: "base", label: "Base" },
  { value: "ethereum", label: "ETH" },
  { value: "bsc", label: "BSC" },
  { value: "arbitrum", label: "ARB" },
  { value: "solana", label: "Solana beta" }
];

function shortAddress(value: string) {
  if (value.length <= 18) return value;
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

function formatTvl(value: number | null) {
  if (value == null) return "TVL неизвестен";
  return new Intl.NumberFormat("ru-RU", {
    notation: "compact",
    maximumFractionDigits: 1,
    style: "currency",
    currency: "USD"
  }).format(value);
}

function formatDateTime(value: string | null) {
  if (!value) return "ещё не было";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit"
  }).format(new Date(value));
}

function formatInterval(seconds: number) {
  if (seconds >= 3600) return `${Math.round(seconds / 3600)} ч`;
  if (seconds >= 60) return `${Math.round(seconds / 60)} мин`;
  return `${seconds} сек`;
}

export function ScoutClient({ compact = false }: { compact?: boolean }) {
  const [targets, setTargets] = useState<ScoutTarget[]>([]);
  const [queued, setQueued] = useState<ScoutQueuedAudit[]>([]);
  const [reviewQueue, setReviewQueue] = useState<ScoutReviewQueue | null>(null);
  const [autopilotStatus, setAutopilotStatus] = useState<ScoutAutopilotStatus | null>(null);
  const [chain, setChain] = useState<Chain | "">("");
  const [limit, setLimit] = useState(3);
  const [minTvl, setMinTvl] = useState(1_000_000);
  const [isLoadingTargets, setIsLoadingTargets] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [autopilotAction, setAutopilotAction] = useState<"refresh" | "start" | "stop" | "run-now" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [lastLimitations, setLastLimitations] = useState<string[]>([]);

  const chainFilter = useMemo(() => (chain ? [chain] : []), [chain]);

  async function loadTargets() {
    setError(null);
    setIsLoadingTargets(true);
    try {
      const next = await discoverScoutTargets({
        limit,
        min_tvl_usd: minTvl,
        chain
      });
      setTargets(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scout не получил список целей");
    } finally {
      setIsLoadingTargets(false);
    }
  }

  async function runScout() {
    setError(null);
    setIsRunning(true);
    try {
      const result = await runScoutOnce({
        limit,
        min_tvl_usd: minTvl,
        chains: chainFilter,
        requested_depth: "preliminary"
      });
      setTargets(result.targets);
      setQueued(result.audits);
      setLastLimitations(result.limitations);
      await loadReviewQueue();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scout-run не запустился");
    } finally {
      setIsRunning(false);
    }
  }

  async function runAllNetworks() {
    setError(null);
    setIsRunningAll(true);
    try {
      const result = await runScoutAllNetworks({
        per_chain_limit: limit,
        min_tvl_usd: minTvl,
        chains: chainFilter,
        requested_depth: "deep"
      });
      setTargets(result.targets);
      setQueued(result.audits);
      setLastLimitations(result.limitations);
      await loadReviewQueue();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Полный цикл по сетям не запустился");
    } finally {
      setIsRunningAll(false);
    }
  }

  async function loadAutopilotStatus() {
    setError(null);
    setAutopilotAction("refresh");
    try {
      const status = await getScoutAutopilotStatus();
      setAutopilotStatus(status);
      if (status.last_result) {
        setTargets(status.last_result.targets);
        setQueued(status.last_result.audits);
        setLastLimitations(status.last_result.limitations);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Статус автопилота не загрузился");
    } finally {
      setAutopilotAction(null);
    }
  }

  async function changeAutopilot(action: "start" | "stop" | "run-now") {
    setError(null);
    setNotice(null);
    setAutopilotAction(action);
    try {
      if (action === "start") {
        const status = await startScoutAutopilot();
        setAutopilotStatus(status);
        setNotice("Автопилот включён. Он будет крутить passive scout-cycle по расписанию.");
      }
      if (action === "stop") {
        const status = await stopScoutAutopilot();
        setAutopilotStatus(status);
        setNotice("Автопилот выключен. Уже созданные аудиты остаются в очереди.");
      }
      if (action === "run-now") {
        const result = await runScoutAutopilotNow({
          per_chain_limit: limit,
          min_tvl_usd: minTvl,
          chains: chainFilter,
          requested_depth: "deep",
          process_queued: true
        });
        setTargets(result.targets);
        setQueued(result.audits);
        setLastLimitations(result.limitations);
        setNotice(`Автопилот прошёл сейчас: найдено ${result.discovered_count}, поставлено ${result.queued_count}.`);
        await loadReviewQueue();
        const status = await getScoutAutopilotStatus();
        setAutopilotStatus(status);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Действие автопилота не выполнилось");
    } finally {
      setAutopilotAction(null);
    }
  }

  async function loadReviewQueue() {
    const queue = await getScoutReviewQueue(150);
    setReviewQueue(queue);
  }

  useEffect(() => {
    void loadTargets();
    void loadReviewQueue();
    void loadAutopilotStatus();
  }, []);

  return (
    <section className={compact ? "scout-console scout-console-compact" : "scout-console"}>
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">24/7 Scout</p>
          <h2>Все сети → глубокий пассивный аудит → очередь отчётов</h2>
        </div>
        <Radar aria-hidden="true" size={25} />
      </div>

      <div className="scout-warning">
        <ShieldCheck aria-hidden="true" size={18} />
        <span>
          Полный режим крутит все поддерживаемые сети по очереди: Base, Ethereum, BSC, Arbitrum и Solana beta.
          wr3 сортирует отчёты на “можно писать”, “проверить вручную” и “пропустить”.
        </span>
      </div>

      <section className="scout-autopilot-panel" aria-label="Статус Scout Autopilot">
        <div className="scout-section-head">
          <strong>Scout Autopilot</strong>
          <span>{autopilotStatus?.running ? "работает" : "остановлен"}</span>
        </div>
        <div className="autopilot-status-grid">
          <div>
            <span>Статус</span>
            <strong>{autopilotStatus?.running ? "Активен" : autopilotStatus?.enabled ? "Включён, ждёт цикл" : "Выключен"}</strong>
          </div>
          <div>
            <span>Интервал</span>
            <strong>{formatInterval(autopilotStatus?.interval_seconds ?? 900)}</strong>
          </div>
          <div>
            <span>Циклов</span>
            <strong>{autopilotStatus?.cycle_count ?? 0}</strong>
          </div>
          <div>
            <span>Всего поставлено</span>
            <strong>{autopilotStatus?.queued_total ?? 0}</strong>
          </div>
          <div>
            <span>Последний запуск</span>
            <strong>{formatDateTime(autopilotStatus?.last_run_at ?? null)}</strong>
          </div>
          <div>
            <span>Следующий запуск</span>
            <strong>{formatDateTime(autopilotStatus?.next_run_at ?? null)}</strong>
          </div>
        </div>
        {autopilotStatus?.last_error ? <p className="error-box">{autopilotStatus.last_error}</p> : null}
        {autopilotStatus?.last_result ? (
          <p className="autopilot-result-line">
            Последний цикл: найдено {autopilotStatus.last_result.discovered_count}, поставлено {autopilotStatus.last_result.queued_count},
            пропущено {autopilotStatus.last_result.skipped_count}.
          </p>
        ) : null}
        <div className="cockpit-actions scout-actions">
          <button type="button" onClick={() => void changeAutopilot("start")} disabled={autopilotAction !== null || autopilotStatus?.running}>
            {autopilotAction === "start" ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <Power aria-hidden="true" size={17} />}
            Включить автопилот
          </button>
          <button type="button" className="secondary-button" onClick={() => void changeAutopilot("stop")} disabled={autopilotAction !== null || !autopilotStatus?.running}>
            {autopilotAction === "stop" ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <Square aria-hidden="true" size={17} />}
            Выключить
          </button>
          <button type="button" onClick={() => void changeAutopilot("run-now")} disabled={autopilotAction !== null}>
            {autopilotAction === "run-now" ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <Radar aria-hidden="true" size={17} />}
            Запустить сейчас
          </button>
          <button type="button" className="secondary-button" onClick={() => void loadAutopilotStatus()} disabled={autopilotAction !== null}>
            {autopilotAction === "refresh" ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <RefreshCw aria-hidden="true" size={17} />}
            Обновить статус
          </button>
        </div>
        {notice ? <p className="empty-state">{notice}</p> : null}
        {autopilotStatus?.limitations.length ? (
          <div className="scout-limits">
            {autopilotStatus.limitations.map((item) => <span key={item}>{item}</span>)}
          </div>
        ) : null}
      </section>

      <div className="scout-controls">
        <label>
          Сеть
          <select value={chain} onChange={(event) => setChain(event.target.value as Chain | "")}>
            {scoutChains.map((item) => <option key={item.value || "all"} value={item.value}>{item.label}</option>)}
          </select>
        </label>
        <label>
          Целей на сеть
          <input
            type="number"
            min={1}
            max={25}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </label>
        <label>
          Мин. TVL $
          <input
            type="number"
            min={0}
            step={100000}
            value={minTvl}
            onChange={(event) => setMinTvl(Number(event.target.value))}
          />
        </label>
      </div>

      <div className="cockpit-actions scout-actions">
        <button type="button" className="secondary-button" onClick={loadTargets} disabled={isLoadingTargets}>
          {isLoadingTargets ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <Activity aria-hidden="true" size={17} />}
          Найти цели
        </button>
        <button type="button" onClick={runScout} disabled={isRunning}>
          {isRunning ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <Play aria-hidden="true" size={17} />}
          Запустить scout-run
        </button>
        <button type="button" onClick={runAllNetworks} disabled={isRunningAll}>
          {isRunningAll ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <Radar aria-hidden="true" size={17} />}
          Крутить все сети глубоко
        </button>
      </div>

      {error ? <p className="error-box">{error}</p> : null}

      <div className="scout-split">
        <div className="scout-list">
          <div className="scout-section-head">
            <strong>Найденные цели</strong>
            <span>{targets.length} шт.</span>
          </div>
          {targets.length === 0 ? (
            <p className="empty-state">Целей пока нет. Нажми “Найти цели”.</p>
          ) : (
            targets.map((target) => (
              <article className="scout-target-card" key={`${target.chain}:${target.address}:${target.slug}`}>
                <div>
                  <span>{target.category || "protocol"}</span>
                  <strong>{target.protocol_name}</strong>
                  <small>{chainLabels[target.chain]} · {shortAddress(target.address)} · {formatTvl(target.tvl_usd)}</small>
                </div>
                <div className="scout-contact-stack">
                  {target.official_url ? <a href={target.official_url} target="_blank" rel="noreferrer">сайт <ExternalLink size={13} /></a> : null}
                  {target.twitter_url ? <a href={target.twitter_url} target="_blank" rel="noreferrer">X <ExternalLink size={13} /></a> : null}
                  {target.security_txt_url ? <a href={target.security_txt_url} target="_blank" rel="noreferrer">security.txt <ExternalLink size={13} /></a> : null}
                </div>
              </article>
            ))
          )}
        </div>

        <div className="scout-list">
          <div className="scout-section-head">
            <strong>Поставлено в аудит</strong>
            <span>{queued.length} шт.</span>
          </div>
          {queued.length === 0 ? (
            <p className="empty-state">После scout-run здесь появятся ссылки на отчёты.</p>
          ) : (
            queued.map((audit) => (
              <article className="scout-audit-card" key={audit.audit_id}>
                <div>
                  <strong>{audit.protocol_name}</strong>
                  <small>{chainLabels[audit.chain]} · {shortAddress(audit.address)}</small>
                </div>
                <Link href={`/audits/${audit.audit_id}?owner_token=${encodeURIComponent(audit.owner_access_token)}`}>
                  Открыть отчёт
                </Link>
              </article>
            ))
          )}
        </div>
      </div>

      <ScoutReviewQueuePanel queue={reviewQueue} />

      {lastLimitations.length ? (
        <div className="scout-limits">
          {lastLimitations.map((item) => <span key={item}>{item}</span>)}
        </div>
      ) : null}
    </section>
  );
}

function ScoutReviewQueuePanel({ queue }: { queue: ScoutReviewQueue | null }) {
  const emptyQueue = {
    ready_to_write: [],
    needs_validation: [],
    skip: [],
    totals: { ready_to_write: 0, needs_validation: 0, skip: 0, total: 0 },
    limitations: []
  } satisfies ScoutReviewQueue;
  const data = queue ?? emptyQueue;
  return (
    <section className="scout-review-board">
      <div className="scout-section-head">
        <strong>Очередь решений после анализа</strong>
        <span>{data.totals.total ?? 0} отчётов</span>
      </div>
      <div className="scout-review-columns">
        <ReviewColumn title="Можно писать" tone="ready" items={data.ready_to_write} empty="Пока нет отчётов, готовых к support." />
        <ReviewColumn title="Проверить вручную" tone="check" items={data.needs_validation} empty="Нет кандидатов на ручную проверку." />
        <ReviewColumn title="Пропустить" tone="skip" items={data.skip} empty="Нет отчётов для пропуска." />
      </div>
    </section>
  );
}

function ReviewColumn({
  title,
  tone,
  items,
  empty
}: {
  title: string;
  tone: "ready" | "check" | "skip";
  items: ScoutReviewItem[];
  empty: string;
}) {
  return (
    <div className={`scout-review-column scout-review-${tone}`}>
      <h3>{title}</h3>
      {items.length === 0 ? <p className="empty-state">{empty}</p> : null}
      {items.slice(0, 8).map((item) => (
        <article className="scout-review-card" key={item.audit_id}>
          <span>{item.action_label}</span>
          <strong>{item.primary_title || `${chainLabels[item.chain]} · ${item.address ? shortAddress(item.address) : shortAddress(item.audit_id)}`}</strong>
          <small>{item.verdict_label} · {item.readiness_label} · score {item.score ?? "?"}</small>
          <p>{item.why}</p>
          {item.evidence_gaps.length ? <em>{item.evidence_gaps[0]}</em> : null}
          <Link href={item.report_url}>Открыть отчёт</Link>
        </article>
      ))}
    </div>
  );
}
