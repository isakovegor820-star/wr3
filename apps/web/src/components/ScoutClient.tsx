"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, ExternalLink, Loader2, Play, Radar, ShieldCheck } from "lucide-react";
import type { Chain, Tier } from "@wr3/shared";
import { chainLabels, tierLabels } from "@/lib/i18n";
import {
  discoverScoutTargets,
  getScoutReviewQueue,
  runScoutAllNetworks,
  runScoutOnce,
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

const scoutTiers: Tier[] = ["free", "hobby", "team", "pro"];

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

export function ScoutClient({ compact = false }: { compact?: boolean }) {
  const [targets, setTargets] = useState<ScoutTarget[]>([]);
  const [queued, setQueued] = useState<ScoutQueuedAudit[]>([]);
  const [reviewQueue, setReviewQueue] = useState<ScoutReviewQueue | null>(null);
  const [chain, setChain] = useState<Chain | "">("");
  const [limit, setLimit] = useState(3);
  const [minTvl, setMinTvl] = useState(1_000_000);
  const [tier, setTier] = useState<Tier>("team");
  const [isLoadingTargets, setIsLoadingTargets] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
        requested_depth: "preliminary",
        tier
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
        requested_depth: "deep",
        tier
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

  async function loadReviewQueue() {
    const queue = await getScoutReviewQueue(150);
    setReviewQueue(queue);
  }

  useEffect(() => {
    void loadTargets();
    void loadReviewQueue();
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
        <label>
          Тариф скана
          <select value={tier} onChange={(event) => setTier(event.target.value as Tier)}>
            {scoutTiers.map((item) => <option key={item} value={item}>{tierLabels[item]}</option>)}
          </select>
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

      <div className="scout-runbook">
        <div>
          <strong>Как держать локально 24/7</strong>
          <code>npm run scout:loop</code>
        </div>
        <p>
          Команда будет раз в 15 минут брать цели по всем сетям, создавать приватные deep-аудиты и складывать результат в review queue.
          Отправка в support остаётся ручной, потому что перед письмом нужен scope и human review.
        </p>
      </div>

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
