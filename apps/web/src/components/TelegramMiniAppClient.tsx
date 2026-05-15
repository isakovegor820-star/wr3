"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Bell,
  Bug,
  CheckCircle2,
  ChevronRight,
  Clipboard,
  ClipboardList,
  ExternalLink,
  FileText,
  LayoutList,
  ListChecks,
  Loader2,
  MoreHorizontal,
  Radar,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  Share2,
  Sparkles,
  Star
} from "lucide-react";
import type { Chain, ScoreBreakdown, Tier } from "@wr3/shared";
import { scoreBand } from "@wr3/shared";
import {
  addWatchlistEntry,
  createAudit,
  getAudit,
  getPublicProject,
  telegramEmulatorCommand,
  verifyTelegramInitData,
  type AuthSession,
  type PublicProjectSummary,
  type TelegramEmulatorResponse,
  type WatchlistEntry
} from "@/lib/api";
import { auditStateLabels, tLimitation, tStatus } from "@/lib/i18n";

type TelegramUser = {
  id?: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
};

type TelegramWebApp = {
  initData: string;
  initDataUnsafe?: { user?: TelegramUser; query_id?: string; start_param?: string };
  version?: string;
  platform?: string;
  colorScheme?: "light" | "dark";
  viewportHeight?: number;
  viewportStableHeight?: number;
  ready?: () => void;
  expand?: () => void;
  close?: () => void;
  openLink?: (url: string) => void;
  onEvent?: (eventType: "viewportChanged", eventHandler: () => void) => void;
  offEvent?: (eventType: "viewportChanged", eventHandler: () => void) => void;
  HapticFeedback?: {
    impactOccurred?: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
    notificationOccurred?: (type: "error" | "success" | "warning") => void;
  };
  MainButton?: {
    setText: (text: string) => TelegramWebApp["MainButton"];
    show: () => TelegramWebApp["MainButton"];
    hide: () => TelegramWebApp["MainButton"];
    enable?: () => TelegramWebApp["MainButton"];
    disable?: () => TelegramWebApp["MainButton"];
    showProgress?: (leaveActive?: boolean) => TelegramWebApp["MainButton"];
    hideProgress?: () => TelegramWebApp["MainButton"];
    onClick?: (callback: () => void) => TelegramWebApp["MainButton"];
    offClick?: (callback: () => void) => TelegramWebApp["MainButton"];
  };
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

type MiniTab = "scan" | "feed" | "bounty" | "watch" | "more";

type ScanResult =
  | {
      ok: true;
      audit_id?: string;
      state?: string;
      status_url?: string;
      limitations?: string[];
      reply?: string;
    }
  | TelegramEmulatorResponse
  | null;

type MiniEvent = {
  id: string;
  kind: "scan" | "score" | "watch" | "bounty" | "system";
  title: string;
  detail: string;
  href?: string;
};

const chains: { value: Chain; label: string; beta?: boolean }[] = [
  { value: "base", label: "Base" },
  { value: "ethereum", label: "ETH" },
  { value: "bsc", label: "BSC" },
  { value: "arbitrum", label: "ARB" },
  { value: "solana", label: "Solana", beta: true }
];

const tabs: { id: MiniTab; label: string; icon: LucideIcon }[] = [
  { id: "scan", label: "Скан", icon: Radar },
  { id: "feed", label: "Очередь", icon: LayoutList },
  { id: "bounty", label: "Баунти", icon: Bug },
  { id: "watch", label: "Алерты", icon: Bell },
  { id: "more", label: "Операции", icon: MoreHorizontal }
];

const demoAddresses: { label: string; chain: Chain; address: string }[] = [
  { label: "Zero", chain: "base", address: "0x0000000000000000000000000000000000000000" },
  { label: "USDC ETH", chain: "ethereum", address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" },
  { label: "Solana демо", chain: "solana", address: "11111111111111111111111111111111" }
];

function commandFor(chain: Chain, address: string, action: "scan" | "watch" | "score") {
  return `/${action} ${chain} ${address || "<address>"}`;
}

function scoreTone(score: number | null | undefined) {
  if (score === null || score === undefined) return "pending";
  return scoreBand(score);
}

function scoreLabel(score: number | null | undefined) {
  const tone = scoreTone(score);
  if (tone === "red") return "Высокий риск";
  if (tone === "yellow") return "Осторожно";
  if (tone === "green") return "Приемлемо";
  if (tone === "blue") return "Отлично";
  return "Нет оценки";
}

function validateAddress(chain: Chain, value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Вставь адрес контракта.";
  if (chain === "solana") {
    return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(trimmed) ? null : "Solana адрес должен быть base58 длиной 32-44 символа.";
  }
  return /^0x[a-fA-F0-9]{40}$/.test(trimmed) ? null : "EVM адрес должен начинаться с 0x и содержать 40 hex символов.";
}

function parseLaunchPayload(raw: string | undefined | null): { chain?: Chain; address?: string } {
  if (!raw) return {};
  const decoded = decodeURIComponent(raw);
  const normalized = decoded.replace(":", "_").replace("/", "_");
  const [maybeChain, ...rest] = normalized.split("_");
  if (chains.some((item) => item.value === maybeChain)) {
    return { chain: maybeChain as Chain, address: rest.join("_") };
  }
  return { address: decoded };
}

export function TelegramMiniAppClient() {
  const [webApp, setWebApp] = useState<TelegramWebApp | null>(null);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [consent, setConsent] = useState(false);
  const [tab, setTab] = useState<MiniTab>("scan");
  const [chain, setChain] = useState<Chain>("base");
  const [tier, setTier] = useState<Tier>("free");
  const [address, setAddress] = useState("0x0000000000000000000000000000000000000000");
  const [bountyScopeConfirmed, setBountyScopeConfirmed] = useState(false);
  const [bountyProgram, setBountyProgram] = useState("training");
  const [scanResult, setScanResult] = useState<ScanResult>(null);
  const [watchResponse, setWatchResponse] = useState<WatchlistEntry | TelegramEmulatorResponse | null>(null);
  const [scoreResponse, setScoreResponse] = useState<PublicProjectSummary | null>(null);
  const [events, setEvents] = useState<MiniEvent[]>([
    {
      id: "boot",
      kind: "system",
      title: "Mini App готов",
      detail: "Можно проверить токен, включить алерты и поделиться безопасным отчётом."
    }
  ]);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isBusy, setIsBusy] = useState<"scan" | "watch" | "score" | "bounty" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const telegramUser = webApp?.initDataUnsafe?.user;
  const isInsideTelegram = Boolean(webApp?.initData);
  const hasTrustedSession = Boolean(session);
  const userLabel = telegramUser?.username ? `@${telegramUser.username}` : telegramUser?.first_name ?? "предпросмотр";
  const latestAuditUrl = scanResult?.status_url;
  const addressError = useMemo(() => validateAddress(chain, address), [address, chain]);
  const safeAddress = address.trim();
  const runtimeDetail = hasTrustedSession ? "приватно" : isInsideTelegram ? "бот" : "превью";

  function pushEvent(event: Omit<MiniEvent, "id">) {
    setEvents((current) => [{ ...event, id: `${Date.now()}-${event.kind}` }, ...current].slice(0, 5));
  }

  useEffect(() => {
    const tg = window.Telegram?.WebApp ?? null;
    if (tg) {
      tg.ready?.();
      tg.expand?.();
      setWebApp(tg);
      const payload = parseLaunchPayload(tg.initDataUnsafe?.start_param);
      if (payload.chain) setChain(payload.chain);
      if (payload.address) setAddress(payload.address);
    }

    const params = new URLSearchParams(window.location.search);
    const queryChain = params.get("chain") as Chain | null;
    const queryAddress = params.get("address");
    if (queryChain && chains.some((item) => item.value === queryChain)) setChain(queryChain);
    if (queryAddress) setAddress(queryAddress);

    const storedTier = window.localStorage.getItem("wr3-local-tier") as Tier | null;
    if (storedTier && ["free", "hobby", "team", "pro"].includes(storedTier)) {
      setTier(storedTier);
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    const syncViewport = () => {
      const stableHeight = webApp?.viewportStableHeight || window.innerHeight;
      const liveHeight = webApp?.viewportHeight || window.innerHeight;
      root.style.setProperty("--tg-viewport-stable-height", `${Math.max(560, stableHeight)}px`);
      root.style.setProperty("--tg-viewport-height", `${Math.max(560, liveHeight)}px`);
    };

    syncViewport();
    window.addEventListener("resize", syncViewport);
    webApp?.onEvent?.("viewportChanged", syncViewport);

    return () => {
      window.removeEventListener("resize", syncViewport);
      webApp?.offEvent?.("viewportChanged", syncViewport);
    };
  }, [webApp]);

  useEffect(() => {
    const mainButton = webApp?.MainButton;
    if (!mainButton) return;
    const label =
      tab === "scan"
        ? "Запустить скан"
        : tab === "bounty"
          ? "Безопасный скан"
          : tab === "watch"
            ? "Включить алерты"
            : tab === "feed"
              ? "Открыть скан"
              : "Открыть скан";
    const handler = () => {
      if (isBusy) return;
      if (tab === "scan") void runScore();
      if (tab === "bounty") void runBountyScan();
      if (tab === "watch") void runWatch();
      if (tab === "feed" || tab === "more") setTab("scan");
    };

    mainButton.setText(label);
    if (isBusy) {
      mainButton.disable?.();
      mainButton.showProgress?.(false);
    } else {
      mainButton.enable?.();
      mainButton.hideProgress?.();
    }
    mainButton.show();
    mainButton.onClick?.(handler);

    return () => {
      mainButton.offClick?.(handler);
      mainButton.hideProgress?.();
      mainButton.hide();
    };
  }, [webApp, tab, isBusy, address, chain, tier, session, bountyScopeConfirmed, bountyProgram]);

  async function connectTelegram() {
    setError(null);
    if (!webApp?.initData) {
      setError("Открой Mini App внутри Telegram, чтобы сервер смог проверить initData.");
      webApp?.HapticFeedback?.notificationOccurred?.("warning");
      return;
    }
    if (!consent) {
      setError("Включи согласие ниже. Это нужно только для приватной wr3-сессии.");
      webApp?.HapticFeedback?.notificationOccurred?.("warning");
      return;
    }
    setIsAuthenticating(true);
    try {
      setSession(
        await verifyTelegramInitData({
          init_data: webApp.initData,
          explicit_account_consent: true
        })
      );
      pushEvent({ kind: "system", title: "Telegram подключён", detail: "Приватные действия теперь идут через проверенную сессию." });
      webApp.HapticFeedback?.notificationOccurred?.("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Telegram initData не прошёл серверную проверку");
      webApp.HapticFeedback?.notificationOccurred?.("error");
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function runBountyScan() {
    setError(null);
    setIsBusy("bounty");
    setScanResult(null);
    try {
      if (!bountyScopeConfirmed) {
        throw new Error("Сначала подтверди правила scope: только in-scope, local/fork/test mode и private disclosure.");
      }
      if (addressError) throw new Error(addressError);
      const audit = await createAudit(
        {
          chain,
          address: safeAddress,
          source: "",
          allow_bytecode_only: true,
          requested_depth: tier === "team" || tier === "pro" ? "standard" : "preliminary",
          visibility: "private",
          user_intent: "third_party_research",
          tier
        },
        session?.bearer_token
      );
      const statusUrl = `/audits/${audit.audit_id}?owner_token=${encodeURIComponent(audit.owner_access_token)}`;
      setScanResult({
        ok: true,
        audit_id: audit.audit_id,
        state: audit.state,
        status_url: statusUrl,
        limitations: audit.limitations,
        reply: `wr3 создал безопасный bounty-скан для ${chain}.`
      });
      pushEvent({
        kind: "bounty",
        title: "Безопасный bounty-скан создан",
        detail: `${chain}:${safeAddress.slice(0, 10)} · ${bountyProgram}`,
        href: statusUrl
      });
      webApp?.HapticFeedback?.impactOccurred?.("light");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bounty-скан не запустился");
      webApp?.HapticFeedback?.notificationOccurred?.("error");
    } finally {
      setIsBusy(null);
    }
  }

  async function runWatch() {
    setError(null);
    setIsBusy("watch");
    try {
      if (addressError) throw new Error(addressError);
      if (session) {
        setWatchResponse(
          await addWatchlistEntry(
            {
              chain,
              address: safeAddress,
              label: "Telegram Mini App",
              alert_channels: ["telegram"]
            },
            session.bearer_token
          )
        );
      } else {
        setWatchResponse(await telegramEmulatorCommand(commandFor(chain, safeAddress, "watch"), telegramUser?.id ?? 1508));
      }
      pushEvent({ kind: "watch", title: "Алерты включены", detail: `${chain}:${safeAddress.slice(0, 10)}` });
      webApp?.HapticFeedback?.notificationOccurred?.("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Алерты не включились");
      webApp?.HapticFeedback?.notificationOccurred?.("error");
    } finally {
      setIsBusy(null);
    }
  }

  async function runScore() {
    setError(null);
    setIsBusy("score");
    try {
      if (addressError) throw new Error(addressError);
      const project = await getPublicProject(chain, safeAddress);
      if (project.score) {
        setScoreResponse(project);
        pushEvent({
          kind: "score",
          title: "Оценка обновлена",
          detail: `${project.score.final_score}/100, ${scoreLabel(project.score.final_score)}`
        });
        webApp?.HapticFeedback?.impactOccurred?.("light");
        return;
      }

      const created = await createAudit(
        {
          chain,
          address: safeAddress,
          source: "",
          allow_bytecode_only: true,
          requested_depth: "preliminary",
          visibility: "private",
          user_intent: "third_party_research",
          tier
        },
        session?.bearer_token
      );
      const statusUrl = `/audits/${created.audit_id}?owner_token=${encodeURIComponent(created.owner_access_token)}`;
      let audit = await getAudit(created.audit_id, created.owner_access_token);
      for (let attempt = 0; attempt < 6 && !audit.score && !["completed", "partial", "failed", "needs_source"].includes(audit.state); attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 650));
        audit = await getAudit(created.audit_id, created.owner_access_token);
      }
      setScanResult({
        ok: true,
        audit_id: created.audit_id,
        state: audit.state,
        status_url: statusUrl,
        limitations: audit.limitations.length ? audit.limitations : created.limitations,
        reply: "wr3 создал быструю проверку риска."
      });
      setScoreResponse({
        chain,
        address: safeAddress,
        score: audit.score,
        safe_harbor_status: false,
        public_findings: [],
        limitations: audit.limitations.length ? audit.limitations : project.limitations
      });
      pushEvent({
        kind: "score",
        title: "Оценка обновлена",
        detail: audit.score ? `${audit.score.final_score}/100, ${scoreLabel(audit.score.final_score)}` : "Скан создан, оценка появится в отчёте",
        href: statusUrl
      });
      webApp?.HapticFeedback?.impactOccurred?.("light");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Оценка не загрузилась");
      webApp?.HapticFeedback?.notificationOccurred?.("error");
    } finally {
      setIsBusy(null);
    }
  }

  return (
    <main className="tg-app-shell">
      <header className="tg-topbar">
        <div className="tg-mini-brand">
          <span className="tg-mini-mark"><Radar aria-hidden="true" size={18} /></span>
          <div>
            <p className="tg-kicker">wr3 команда</p>
            <h1>Рабочий cockpit</h1>
          </div>
        </div>
        <div className={`tg-runtime-pill ${hasTrustedSession ? "tg-runtime-pill-ok" : ""}`}>
          {hasTrustedSession ? <ShieldCheck aria-hidden="true" size={15} /> : <Sparkles aria-hidden="true" size={15} />}
          <span>{runtimeDetail}</span>
        </div>
      </header>

      <section className="tg-screen-card">
        {tab === "scan" ? (
          <ScanScreen
            address={address}
            addressError={addressError}
            chain={chain}
            error={error}
            events={events}
            isBusy={isBusy === "score"}
            latestAuditUrl={latestAuditUrl}
            onAddressChange={setAddress}
            onChainChange={setChain}
            onPickDemo={(demo) => {
              setChain(demo.chain);
              setAddress(demo.address);
            }}
            onRunScore={runScore}
            scoreResponse={scoreResponse}
            scanResult={scanResult}
            tier={tier}
          />
        ) : null}

        {tab === "feed" ? (
          <FeedScreen
            events={events}
            latestAuditUrl={latestAuditUrl}
            scanResult={scanResult}
            scoreResponse={scoreResponse}
            watchResponse={watchResponse}
          />
        ) : null}

        {tab === "bounty" ? (
          <BountyScreen
            address={address}
            addressError={addressError}
            bountyProgram={bountyProgram}
            bountyScopeConfirmed={bountyScopeConfirmed}
            chain={chain}
            error={error}
            isBusy={isBusy === "bounty"}
            latestAuditUrl={latestAuditUrl}
            onAddressChange={setAddress}
            onBountyProgramChange={setBountyProgram}
            onBountyScopeChange={setBountyScopeConfirmed}
            onChainChange={setChain}
            onRunBountyScan={runBountyScan}
            scanResult={scanResult}
          />
        ) : null}

        {tab === "watch" ? (
          <WatchScreen
            address={address}
            addressError={addressError}
            chain={chain}
            error={error}
            isBusy={isBusy === "watch"}
            onAddressChange={setAddress}
            onChainChange={setChain}
            onRunWatch={runWatch}
            watchResponse={watchResponse}
          />
        ) : null}

        {tab === "more" ? (
          <MoreScreen
            consent={consent}
            error={error}
            hasTrustedSession={hasTrustedSession}
            isAuthenticating={isAuthenticating}
            isInsideTelegram={isInsideTelegram}
            onConnect={connectTelegram}
            setConsent={setConsent}
            setTier={setTier}
            tier={tier}
            userLabel={userLabel}
          />
        ) : null}
      </section>

      <nav className="tg-bottom-nav" aria-label="Mini App навигация">
        {tabs.map((item) => {
          const Icon = item.icon;
          return (
            <button type="button" key={item.id} className={tab === item.id ? "tg-nav-item tg-nav-item-active" : "tg-nav-item"} onClick={() => setTab(item.id)}>
              <Icon aria-hidden="true" size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </main>
  );
}

function MiniInput({
  address,
  addressError,
  onAddressChange
}: {
  address: string;
  addressError: string | null;
  onAddressChange: (value: string) => void;
}) {
  return (
    <label className="tg-field">
      <span>Адрес контракта</span>
      <input value={address} onChange={(event) => onAddressChange(event.target.value.trim())} inputMode="text" autoComplete="off" spellCheck={false} />
      {addressError ? <small>{addressError}</small> : null}
    </label>
  );
}

function ChainPicker({ chain, onChainChange }: { chain: Chain; onChainChange: (value: Chain) => void }) {
  return (
    <section className="tg-chain-strip tg-inline-chain-strip" aria-label="Выбор сети">
      {chains.map((item) => (
        <button
          type="button"
          className={chain === item.value ? "tg-chain-chip tg-chain-chip-active" : "tg-chain-chip"}
          key={item.value}
          onClick={() => onChainChange(item.value)}
        >
          {item.label}
          {item.beta ? <span>beta</span> : null}
        </button>
      ))}
    </section>
  );
}

function FeedScreen({
  events,
  latestAuditUrl,
  scanResult,
  scoreResponse,
  watchResponse
}: {
  events: MiniEvent[];
  latestAuditUrl?: string;
  scanResult: ScanResult;
  scoreResponse: PublicProjectSummary | null;
  watchResponse: WatchlistEntry | TelegramEmulatorResponse | null;
}) {
  const watchStatus = watchResponse ? ("status" in watchResponse ? tStatus(watchResponse.status) : watchResponse.ok ? "активно" : "ошибка") : "не включены";
  const score = scoreResponse?.score?.final_score ?? null;
  const bountyStatus = events.some((event) => event.kind === "bounty") ? "создан" : "нет";

  return (
    <div className="tg-screen tg-feed-screen">
      <ScreenTitle icon={LayoutList} title="Очередь находок" subtitle="Скан, баунти, алерты и последние действия команды" />

      <div className="tg-feed-metrics" aria-label="Сводка Mini App">
        <div>
          <span>Скан</span>
          <strong>{scanResult?.audit_id ? "создан" : "нет"}</strong>
        </div>
        <div>
          <span>Риск</span>
          <strong>{score ?? "--"}</strong>
        </div>
        <div>
          <span>Баунти</span>
          <strong>{bountyStatus}</strong>
        </div>
        <div>
          <span>Алерты</span>
          <strong>{watchStatus}</strong>
        </div>
      </div>

      {scanResult ? <ScanResultCard result={scanResult} latestAuditUrl={latestAuditUrl} /> : null}
      {scoreResponse ? (
        <ScoreCard
          score={scoreResponse.score}
          findingsCount={scoreResponse.public_findings.length}
          limitations={scoreResponse.limitations}
        />
      ) : null}

      <ActivityList events={events} />
    </div>
  );
}

function ScanScreen({
  address,
  addressError,
  chain,
  error,
  events,
  isBusy,
  latestAuditUrl,
  onAddressChange,
  onChainChange,
  onPickDemo,
  onRunScore,
  scoreResponse,
  scanResult,
  tier
}: {
  address: string;
  addressError: string | null;
  chain: Chain;
  error: string | null;
  events: MiniEvent[];
  isBusy: boolean;
  latestAuditUrl?: string;
  onAddressChange: (value: string) => void;
  onChainChange: (value: Chain) => void;
  onPickDemo: (demo: { chain: Chain; address: string }) => void;
  onRunScore: () => Promise<void>;
  scoreResponse: PublicProjectSummary | null;
  scanResult: ScanResult;
  tier: Tier;
}) {
  const score = scoreResponse?.score ?? null;
  return (
    <form
      className="tg-screen"
      onSubmit={(event) => {
        event.preventDefault();
        void onRunScore();
      }}
    >
      <ScreenTitle icon={Radar} title="Быстрый скан" subtitle="Адрес → задача аудита → очередь находок" />
      <ChainPicker chain={chain} onChainChange={onChainChange} />
      <MiniInput address={address} addressError={addressError} onAddressChange={onAddressChange} />

      <div className="tg-quick-grid" aria-label="Демо адреса">
        {demoAddresses.map((demo) => (
          <button type="button" key={demo.label} onClick={() => onPickDemo(demo)}>
          {demo.label}
          </button>
        ))}
      </div>

      <CommandPreview command={commandFor(chain, address, "score")} />

      <button type="submit" className="tg-primary-button" disabled={isBusy}>
        {isBusy ? <Loader2 className="spin" aria-hidden="true" size={18} /> : <Radar aria-hidden="true" size={18} />}
        Запустить скан
      </button>

      <InlineError error={error} />
      <MiniVerdictCard score={score} />
      <MiniNextAction score={score} />
      <ScoreCard score={score} findingsCount={scoreResponse?.public_findings.length ?? 0} limitations={scoreResponse?.limitations ?? []} />
      <MiniShareCard score={score} chain={chain} address={address} />
      {scanResult ? <ScanResultCard result={scanResult} latestAuditUrl={latestAuditUrl} /> : null}
      <ActivityList events={events} />
    </form>
  );
}

function BountyScreen({
  address,
  addressError,
  bountyProgram,
  bountyScopeConfirmed,
  chain,
  error,
  isBusy,
  latestAuditUrl,
  onAddressChange,
  onBountyProgramChange,
  onBountyScopeChange,
  onChainChange,
  onRunBountyScan,
  scanResult
}: {
  address: string;
  addressError: string | null;
  bountyProgram: string;
  bountyScopeConfirmed: boolean;
  chain: Chain;
  error: string | null;
  isBusy: boolean;
  latestAuditUrl?: string;
  onAddressChange: (value: string) => void;
  onBountyProgramChange: (value: string) => void;
  onBountyScopeChange: (value: boolean) => void;
  onChainChange: (value: Chain) => void;
  onRunBountyScan: () => Promise<void>;
  scanResult: ScanResult;
}) {
  const checklist = [
    "Проверить, что программа реально принимает этот контракт.",
    "Не запускать mainnet-транзакции и не трогать чужие средства.",
    "Валидировать кандидата вручную в локальном/fork/test режиме.",
    "Писать приватный репорт без публичного PoC до disclosure window."
  ];

  return (
    <div className="tg-screen tg-bounty-screen">
      <ScreenTitle icon={Bug} title="Радар bug bounty" subtitle="Scope → безопасный скан → кандидатный отчёт" />
      <label className="tg-field">
        <span>Программа</span>
        <select value={bountyProgram} onChange={(event) => onBountyProgramChange(event.target.value)}>
          <option value="training">Тренировка / локальные примеры</option>
          <option value="authorized">Разрешённая программа</option>
          <option value="safe-harbor">Scope Safe Harbor</option>
        </select>
      </label>

      <article className="tg-bounty-scope-card">
        <div>
          <ShieldCheck aria-hidden="true" size={18} />
          <strong>Правила scope</strong>
        </div>
        <p>wr3 в Mini App делает только passive analysis и безопасный queued scan. Никаких live exploit steps, broadcast, приватных ключей или публичных обвинений.</p>
      </article>

      <label className="tg-toggle-row">
        <input type="checkbox" checked={bountyScopeConfirmed} onChange={(event) => onBountyScopeChange(event.target.checked)} />
        <span>Я проверил scope и буду валидировать кандидаты только безопасно.</span>
      </label>

      <ChainPicker chain={chain} onChainChange={onChainChange} />
      <MiniInput address={address} addressError={addressError} onAddressChange={onAddressChange} />
      <CommandPreview command={commandFor(chain, address, "scan")} />
      <button type="button" className="tg-primary-button" disabled={isBusy || !bountyScopeConfirmed} onClick={onRunBountyScan}>
        {isBusy ? <Loader2 className="spin" aria-hidden="true" size={18} /> : <Bug aria-hidden="true" size={18} />}
        Безопасный скан
      </button>
      <InlineError error={error} />

      <article className="tg-bounty-checklist">
        <div className="tg-activity-title">
          <ListChecks aria-hidden="true" size={16} />
          <strong>Чеклист ручной проверки</strong>
        </div>
        {checklist.map((item) => (
          <div className="tg-bounty-check-row" key={item}>
            <CheckCircle2 aria-hidden="true" size={15} />
            <span>{item}</span>
          </div>
        ))}
      </article>

      {scanResult ? <ScanResultCard result={scanResult} latestAuditUrl={latestAuditUrl} /> : (
        <article className="tg-empty-card">
          <Bug aria-hidden="true" size={20} />
          <span>Кандидатов пока нет. Запусти безопасный скан после проверки scope.</span>
        </article>
      )}

      <article className="tg-bounty-report-card">
        <div>
          <FileText aria-hidden="true" size={17} />
          <strong>Черновик отчёта</strong>
        </div>
        <p>После скана здесь останется приватная ссылка на audit. В отчёт добавляй: scope, impact, безопасные шаги воспроизведения в local/fork/test mode и recommendation.</p>
      </article>
    </div>
  );
}

function WatchScreen({
  address,
  addressError,
  chain,
  error,
  isBusy,
  onAddressChange,
  onChainChange,
  onRunWatch,
  watchResponse
}: {
  address: string;
  addressError: string | null;
  chain: Chain;
  error: string | null;
  isBusy: boolean;
  onAddressChange: (value: string) => void;
  onChainChange: (value: Chain) => void;
  onRunWatch: () => Promise<void>;
  watchResponse: WatchlistEntry | TelegramEmulatorResponse | null;
}) {
  const status = watchResponse ? ("status" in watchResponse ? tStatus(watchResponse.status) : watchResponse.ok ? "активно" : "ошибка") : "не включено";

  return (
    <div className="tg-screen">
      <ScreenTitle icon={Bell} title="Алерты" subtitle="Уведомления об изменениях и новых сигналах высокого риска" />
      <ChainPicker chain={chain} onChainChange={onChainChange} />
      <MiniInput address={address} addressError={addressError} onAddressChange={onAddressChange} />
      <CommandPreview command={commandFor(chain, address, "watch")} />
      <button type="button" className="tg-primary-button" disabled={isBusy} onClick={onRunWatch}>
        {isBusy ? <Loader2 className="spin" aria-hidden="true" size={18} /> : <Bell aria-hidden="true" size={18} />}
        Включить алерты
      </button>
      <InlineError error={error} />
      <article className="tg-state-card">
        <div className="tg-state-icon"><Bell aria-hidden="true" size={18} /></div>
        <div>
          <strong>{status}</strong>
          <span>{watchResponse ? "Контракт добавлен в список наблюдения. В localhost это проверяет сценарий без реального Telegram-пуша." : "Пока алерты не включены."}</span>
        </div>
      </article>
    </div>
  );
}

function MoreScreen({
  consent,
  error,
  hasTrustedSession,
  isAuthenticating,
  isInsideTelegram,
  onConnect,
  setConsent,
  setTier,
  tier,
  userLabel
}: {
  consent: boolean;
  error: string | null;
  hasTrustedSession: boolean;
  isAuthenticating: boolean;
  isInsideTelegram: boolean;
  onConnect: () => Promise<void>;
  setConsent: (value: boolean) => void;
  setTier: (value: Tier) => void;
  tier: Tier;
  userLabel: string;
}) {
  return (
    <div className="tg-screen tg-profile-screen">
      <ScreenTitle icon={MoreHorizontal} title="Операции" subtitle={userLabel} />
      <article className="tg-state-card">
        <div className="tg-state-icon">{hasTrustedSession ? <ShieldCheck aria-hidden="true" size={18} /> : <ShieldQuestion aria-hidden="true" size={18} />}</div>
        <div>
          <strong>{hasTrustedSession ? "Проверенная Telegram-сессия" : isInsideTelegram ? "Режим бота без приватной сессии" : "Предпросмотр localhost"}</strong>
          <span>{hasTrustedSession ? "Приватные действия аудита и алертов доступны." : "Скан, оценка риска и алерты работают. Приватную сессию можно включить только здесь."}</span>
        </div>
      </article>

      <label className="tg-toggle-row">
        <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
        <span>Разрешить приватную wr3-сессию.</span>
      </label>

      <button type="button" className="tg-primary-button tg-profile-connect" disabled={isAuthenticating} onClick={onConnect}>
        {isAuthenticating ? <Loader2 className="spin" aria-hidden="true" size={18} /> : <ShieldCheck aria-hidden="true" size={18} />}
        Подключить Telegram
      </button>

      <label className="tg-field">
        <span>Локальный симулятор тарифа</span>
        <select
          value={tier}
          onChange={(event) => {
            const nextTier = event.target.value as Tier;
            setTier(nextTier);
            window.localStorage.setItem("wr3-local-tier", nextTier);
          }}
        >
          <option value="free">Бесплатный</option>
          <option value="hobby">Хобби</option>
          <option value="team">Команда</option>
          <option value="pro">Про</option>
        </select>
      </label>

      <div className="tg-link-grid">
        <Link href="/telegram-emulator">Эмулятор</Link>
        <Link href="/dashboard">Панель</Link>
        <Link href="/tools">Движок</Link>
        <Link href="/integrations">Статус API</Link>
      </div>
      <InlineError error={error} />
    </div>
  );
}

function miniVerdict(score: number | null | undefined) {
  if (score === null || score === undefined) {
    return {
      tone: "pending",
      title: "Недостаточно данных",
      action: "Не принимай решение только по этому экрану. Запусти проверку ещё раз позже или включи алерты."
    };
  }
  const tone = scoreTone(score);
  if (tone === "red") return { tone, title: "Высокий риск", action: "wr3 не рекомендует входить без дополнительной проверки." };
  if (tone === "yellow") return { tone, title: "Осторожно", action: "Проверь причины и не заходи на сумму, которую не готов потерять." };
  if (tone === "green") return { tone, title: "Выглядит нормально", action: "Критичных публичных сигналов не видно, но гарантий нет." };
  return { tone, title: "Сильный профиль", action: "Риск выглядит ниже среднего. Всё равно следи за изменениями." };
}

function MiniVerdictCard({ score }: { score: ScoreBreakdown | null }) {
  const verdict = miniVerdict(score?.final_score);
  return (
    <article className={`tg-mini-verdict tg-mini-verdict-${verdict.tone}`}>
      <div>
        <span>Вердикт</span>
        <strong>{verdict.title}</strong>
        <p>{verdict.action}</p>
      </div>
      <b>{score?.final_score ?? "--"}</b>
    </article>
  );
}

function MiniNextAction({ score }: { score: ScoreBreakdown | null }) {
  const verdict = miniVerdict(score?.final_score);
  return (
    <article className="tg-state-card">
      <div className="tg-state-icon"><ShieldAlert aria-hidden="true" size={18} /></div>
      <div>
        <strong>Что делать сейчас</strong>
        <span>{verdict.action} Это не инвестиционный совет.</span>
      </div>
    </article>
  );
}

function MiniShareCard({ score, chain, address }: { score: ScoreBreakdown | null; chain: Chain; address: string }) {
  const verdict = miniVerdict(score?.final_score);
  const [origin, setOrigin] = useState("");
  const publicPath = `/p/${chain}/${address}`;
  const url = origin ? new URL(publicPath, origin).toString() : publicPath;
  const text = `wr3 risk-check: ${verdict.title}${score ? ` (${score.final_score}/100)` : ""}\n${verdict.action}\n${url}`;
  const href = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;

  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  return (
    <article className="tg-share-card">
      <div>
        <Share2 aria-hidden="true" size={17} />
        <strong>Поделиться отчётом</strong>
      </div>
      <p>{text}</p>
      <a href={href} target="_blank" rel="noreferrer">Отправить в Telegram</a>
    </article>
  );
}

function CommandPreview({ command }: { command: string }) {
  return (
    <div className="tg-command-preview">
      <Clipboard aria-hidden="true" size={15} />
      <span>{command}</span>
    </div>
  );
}

function ScreenTitle({ icon: Icon, title, subtitle }: { icon: LucideIcon; title: string; subtitle: string }) {
  return (
    <div className="tg-screen-title">
      <span><Icon aria-hidden="true" size={18} /></span>
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}

function ActivityList({ events }: { events: MiniEvent[] }) {
  return (
    <article className="tg-activity-card">
      <div className="tg-activity-title">
        <Activity aria-hidden="true" size={16} />
        <strong>Последние действия</strong>
      </div>
      <div className="tg-action-list">
        {events.map((event) => (
          <div className="tg-action-row" key={event.id}>
            <span>{event.kind}</span>
            <div>
              <strong>{event.title}</strong>
              <p>{event.detail}</p>
            </div>
            {event.href ? (
              <Link href={event.href} aria-label="Открыть результат">
                <ExternalLink aria-hidden="true" size={15} />
              </Link>
            ) : null}
          </div>
        ))}
      </div>
    </article>
  );
}

function ScanResultCard({ result, latestAuditUrl }: { result: ScanResult; latestAuditUrl?: string }) {
  if (!result) {
    return (
      <article className="tg-empty-card">
        <ClipboardList aria-hidden="true" size={20} />
        <span>После запуска здесь появится ссылка на отчёт.</span>
      </article>
    );
  }

  return (
    <article className="tg-result-card">
      <div className="tg-result-head">
        <CheckCircle2 aria-hidden="true" size={19} />
        <div>
          <strong>{result.state ? `Состояние: ${auditStateLabels[result.state as keyof typeof auditStateLabels] ?? result.state}` : result.ok ? "Команда обработана" : "Ошибка команды"}</strong>
          <span>{result.audit_id ? `Аудит ${result.audit_id.slice(0, 8)}` : result.reply ?? "Telegram-сценарий завершён"}</span>
        </div>
      </div>
      {result.limitations && result.limitations.length > 0 ? <p className="tg-helper">{result.limitations.slice(0, 2).map(tLimitation).join(" · ")}</p> : null}
      {latestAuditUrl ? (
        <Link className="tg-open-report" href={latestAuditUrl}>
          Открыть отчёт <ChevronRight aria-hidden="true" size={16} />
        </Link>
      ) : null}
    </article>
  );
}

function ScoreCard({ score, findingsCount, limitations }: { score: ScoreBreakdown | null; findingsCount: number; limitations: string[] }) {
  if (!score) {
    return (
      <article className="tg-empty-card">
        <Star aria-hidden="true" size={20} />
        <span>Оценка ещё не загружена.</span>
      </article>
    );
  }

  const rows = [
    ["Код", score.code_security_score],
    ["Центр.", score.centralization_score],
    ["Ликвид.", score.liquidity_score],
    ["Команда", score.team_kyc_score],
    ["Поведение", score.behavior_score]
  ] as const;

  return (
    <article className={`tg-score-card tg-score-${scoreTone(score.final_score)}`}>
      <div className="tg-score-main">
        <div>
          <strong>{score.final_score}</strong>
          <span>{scoreLabel(score.final_score)}</span>
        </div>
        <p>{findingsCount} публичных находок</p>
      </div>
      <div className="tg-score-bars">
        {rows.map(([label, value]) => (
          <div className="tg-score-row" key={label}>
            <span>{label}</span>
            <div aria-hidden="true"><i style={{ width: `${value}%` }} /></div>
            <b>{value}</b>
          </div>
        ))}
      </div>
      {limitations.length > 0 ? <p className="tg-helper">{limitations.slice(0, 2).map(tLimitation).join(" · ")}</p> : null}
    </article>
  );
}

function InlineError({ error }: { error: string | null }) {
  return error ? <p className="tg-inline-error">{error}</p> : null;
}
