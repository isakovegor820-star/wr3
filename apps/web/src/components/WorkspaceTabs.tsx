"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Bell,
  BookOpen,
  Bug,
  CheckSquare,
  Clipboard,
  FileText,
  Loader2,
  Radar,
  RefreshCw,
  Send,
  Share2,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Star,
  TriangleAlert
} from "lucide-react";
import type { AuditSummary, Chain, Finding, ScoreBreakdown } from "@wr3/shared";
import { scoreBand } from "@wr3/shared";
import {
  createDisclosureCase,
  createAudit,
  getAudit,
  getFindings,
  getPublicProject,
  getToolsStatus,
  listAudits,
  telegramEmulatorCommand,
  type DashboardAudit,
  type DisclosureCase,
  type PublicProjectSummary,
  type TelegramEmulatorResponse,
  type ToolsStatusResponse
} from "@/lib/api";
import { auditStateLabels, chainLabels, severityLabels, tFindingText, tLimitation } from "@/lib/i18n";

type BuyerTab = "check" | "risk" | "bounty" | "alerts" | "learn" | "engine";
type BuyerResult = {
  chain: Chain;
  address: string;
  score: ScoreBreakdown | null;
  findings: Finding[];
  limitations: string[];
  audit?: AuditSummary;
  auditHref?: string;
  publicHref: string;
};

const tabs: Array<{ id: BuyerTab; label: string; note: string; icon: typeof Radar }> = [
  { id: "check", label: "Проверить токен", note: "адрес → вердикт", icon: Radar },
  { id: "risk", label: "Высокий риск", note: "осторожная лента", icon: Siren },
  { id: "bounty", label: "Bug Bounty", note: "research mode", icon: Bug },
  { id: "alerts", label: "Мои алерты", note: "следить за токеном", icon: Bell },
  { id: "learn", label: "Объяснения", note: "простыми словами", icon: BookOpen },
  { id: "engine", label: "Движок", note: "tools status", icon: CheckSquare }
];

const chains: { value: Chain; label: string; beta?: boolean }[] = [
  { value: "base", label: "Base" },
  { value: "ethereum", label: "ETH" },
  { value: "bsc", label: "BSC" },
  { value: "arbitrum", label: "ARB" },
  { value: "solana", label: "Solana", beta: true }
];

const examples: { label: string; chain: Chain; address: string }[] = [
  { label: "Zero demo", chain: "base", address: "0x0000000000000000000000000000000000000000" },
  { label: "USDC", chain: "ethereum", address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" },
  { label: "Solana demo", chain: "solana", address: "11111111111111111111111111111111" }
];

const explainers = [
  {
    title: "Owner",
    short: "Адрес, который может управлять контрактом.",
    detail: "Если owner один обычный кошелёк, он может быть слабым местом: потеря ключа или злой владелец меняют риск."
  },
  {
    title: "Mint",
    short: "Возможность выпускать новые токены.",
    detail: "Если mint не ограничен, supply может резко вырасти. Для покупателя это риск размывания цены."
  },
  {
    title: "Proxy",
    short: "Контракт можно обновить после запуска.",
    detail: "Proxy не всегда плохо, но покупателю важно знать, кто может заменить логику и насколько это контролируется."
  },
  {
    title: "Liquidity",
    short: "Насколько легко выйти из позиции.",
    detail: "Мало ликвидности или слабая блокировка LP повышают риск, что продать токен будет трудно."
  }
];

const bountyPrograms = [
  {
    id: "custom",
    name: "Custom authorized program",
    badge: "ручной scope",
    scope: [
      "Проверить официальный bounty/scope перед запуском.",
      "Сканировать только assets, где есть явное разрешение.",
      "Работать passive/local/fork/testnet, без mainnet-транзакций.",
      "Отправлять находки приватно через официальный канал программы."
    ]
  },
  {
    id: "safe-harbor",
    name: "Safe Harbor / explicit authorization",
    badge: "только opt-in",
    scope: [
      "Активная проверка разрешена только при явном scope или Safe Harbor opt-in.",
      "Даже при opt-in сначала использовать локальный fork/test-validator.",
      "Не перемещать средства, не делать DoS, не публиковать working exploit.",
      "Фиксировать timeline disclosure и contact log."
    ]
  },
  {
    id: "learning",
    name: "Training / local fixtures",
    badge: "безопасно",
    scope: [
      "Использовать локальные fixtures, CTF, testnet или собственный код.",
      "Можно тренировать triage, checklist и report writing.",
      "Нельзя выдавать учебный кейс за bounty-ready находку.",
      "Подходит для набора навыка без юридического риска."
    ]
  }
] as const;

const validationChecklist = [
  "Scope программы подтверждён по официальной странице.",
  "Asset точно входит в разрешённую область проверки.",
  "Проверка выполнялась passive/local/fork/testnet.",
  "Нет mainnet-транзакций, перемещения средств или DoS.",
  "False positive проверен вручную.",
  "Impact описан без преувеличения и обвинений.",
  "Есть понятная recommendation/mitigation."
];

function validateAddress(chain: Chain, value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Вставь адрес токена или контракта.";
  if (chain === "solana") {
    return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(trimmed) ? null : "Solana адрес должен быть base58 длиной 32-44 символа.";
  }
  return /^0x[a-fA-F0-9]{40}$/.test(trimmed) ? null : "EVM адрес должен начинаться с 0x и содержать 40 hex символов.";
}

function verdictFor(score: number | null | undefined) {
  if (score === null || score === undefined) {
    return {
      tone: "pending",
      title: "Недостаточно данных",
      action: "Не принимай решение только по этому экрану. Запусти проверку или включи алерты.",
      label: "данных мало"
    };
  }
  const band = scoreBand(score);
  if (band === "red") {
    return {
      tone: "red",
      title: "Высокий риск",
      action: "wr3 не рекомендует входить без дополнительной проверки.",
      label: "лучше подождать"
    };
  }
  if (band === "yellow") {
    return {
      tone: "yellow",
      title: "Осторожно",
      action: "Проверь причины ниже и не заходи на сумму, которую не готов потерять.",
      label: "требует внимания"
    };
  }
  if (band === "green") {
    return {
      tone: "green",
      title: "Выглядит нормально",
      action: "Критичных сигналов не видно, но это не гарантия безопасности.",
      label: "без гарантий"
    };
  }
  return {
    tone: "blue",
    title: "Сильный профиль",
    action: "Риск выглядит ниже среднего, но следить за изменениями всё равно полезно.",
    label: "низкий риск"
  };
}

function safeReasons(result: BuyerResult | null): string[] {
  if (!result) return ["Проверка ещё не запускалась.", "wr3 покажет только безопасные публичные причины.", "Exploit/PoC детали обычному пользователю не показываются."];
  const reasons = result.findings.slice(0, 3).map((finding) => tFindingText(finding.summary));
  if (result.limitations.includes("no_public_wr3_audit_for_contract")) {
    reasons.push("По этому адресу ещё нет публичного wr3-отчёта.");
  }
  if (result.limitations.some((item) => item.includes("unverified") || item.includes("source"))) {
    reasons.push("Исходный код или источник данных может быть неполным.");
  }
  if (result.score?.caps_applied.length) {
    reasons.push("Оценка ограничена жёсткими safety-правилами wr3.");
  }
  return [...new Set(reasons)].slice(0, 3);
}

function shareText(result: BuyerResult | null, chain: Chain, address: string) {
  const score = result?.score?.final_score;
  const verdict = verdictFor(score);
  const href = result?.publicHref ?? `/p/${chain}/${address}`;
  return `wr3 risk-check: ${verdict.title}${score === undefined || score === null ? "" : ` (${score}/100)`}\n${verdict.action}\n${href}`;
}

export function WorkspaceTabs() {
  const [activeTab, setActiveTab] = useState<BuyerTab>("check");

  return (
    <section className="workbench buyer-workbench" aria-label="Ленты wr3 для покупателя токена">
      <nav className="workbench-tabs buyer-tabs" aria-label="Разделы wr3">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              type="button"
              key={tab.id}
              className={activeTab === tab.id ? "workbench-tab workbench-tab-active" : "workbench-tab"}
              onClick={() => setActiveTab(tab.id)}
              aria-pressed={activeTab === tab.id}
            >
              <Icon aria-hidden="true" size={20} />
              <span>{tab.label}</span>
              <small>{tab.note}</small>
            </button>
          );
        })}
      </nav>

      <div className="workbench-feed" aria-live="polite">
        {activeTab === "check" ? <TokenCheckFeed onOpenBounty={() => setActiveTab("bounty")} /> : null}
        {activeTab === "risk" ? <HighRiskFeed /> : null}
        {activeTab === "bounty" ? <BugBountyFeed /> : null}
        {activeTab === "alerts" ? <BuyerAlertsFeed /> : null}
        {activeTab === "learn" ? <ExplainersFeed /> : null}
        {activeTab === "engine" ? <EngineReadinessFeed /> : null}
      </div>
    </section>
  );
}

function TokenCheckFeed({ onOpenBounty }: { onOpenBounty: () => void }) {
  const [chain, setChain] = useState<Chain>("base");
  const [address, setAddress] = useState("0x0000000000000000000000000000000000000000");
  const [result, setResult] = useState<BuyerResult | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const addressError = useMemo(() => validateAddress(chain, address), [chain, address]);

  async function pollAudit(auditId: string, ownerToken: string) {
    for (let attempt = 0; attempt < 8; attempt += 1) {
      const audit = await getAudit(auditId, ownerToken);
      if (audit.score || ["completed", "partial", "failed", "needs_source"].includes(audit.state)) {
        return audit;
      }
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
    return getAudit(auditId, ownerToken);
  }

  async function checkToken() {
    setError(null);
    const trimmed = address.trim();
    if (addressError) {
      setError(addressError);
      return;
    }
    setIsChecking(true);
    try {
      const publicProject = await getPublicProject(chain, trimmed);
      if (publicProject.score) {
        setResult(fromPublicProject(publicProject));
        return;
      }

      const created = await createAudit({
        chain,
        address: trimmed,
        source: "",
        allow_bytecode_only: true,
        requested_depth: "preliminary",
        visibility: "private",
        user_intent: "third_party_research",
        tier: "free"
      });
      const audit = await pollAudit(created.audit_id, created.owner_access_token);
      setResult({
        chain,
        address: trimmed,
        score: audit.score,
        findings: [],
        limitations: audit.limitations,
        audit,
        auditHref: `/audits/${created.audit_id}?owner_token=${encodeURIComponent(created.owner_access_token)}`,
        publicHref: `/p/${chain}/${trimmed}`
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не получилось проверить токен");
    } finally {
      setIsChecking(false);
    }
  }

  return (
    <div className="buyer-check-layout">
      <section className="buyer-check-card">
        <div className="buyer-check-head">
          <div>
            <p className="eyebrow">Проверить токен</p>
            <h2>Вставь адрес. Получи понятный риск.</h2>
          </div>
          <Radar aria-hidden="true" size={30} />
        </div>

        <ChainPicker chain={chain} onChainChange={setChain} />

        <label className="buyer-address-field">
          <span>Адрес токена или контракта</span>
          <input value={address} onChange={(event) => setAddress(event.target.value.trim())} placeholder="0x..." />
          {addressError ? <small>{addressError}</small> : null}
        </label>

        <div className="buyer-example-row">
          {examples.map((example) => (
            <button
              type="button"
              className="secondary-button"
              key={example.label}
              onClick={() => {
                setChain(example.chain);
                setAddress(example.address);
              }}
            >
              {example.label}
            </button>
          ))}
        </div>

        <button type="button" className="buyer-primary" disabled={isChecking} onClick={checkToken}>
          {isChecking ? <Loader2 className="spin" aria-hidden="true" size={18} /> : <ShieldCheck aria-hidden="true" size={18} />}
          Проверить риск
        </button>
        {error ? <p className="error-box">{error}</p> : null}
      </section>

      <section className="buyer-result-stack">
        <VerdictCard result={result} chain={chain} address={address} />
        <NextActionCard result={result} chain={chain} address={address} onOpenBounty={onOpenBounty} />
        <ReasonsCard result={result} />
        <ShareCard result={result} chain={chain} address={address} />
        <TechnicalDetails result={result} />
      </section>
    </div>
  );
}

function ChainPicker({ chain, onChainChange }: { chain: Chain; onChainChange: (chain: Chain) => void }) {
  return (
    <div className="segment-row buyer-chain-picker" aria-label="Выбор сети">
      {chains.map((item) => (
        <button
          type="button"
          key={item.value}
          className={chain === item.value ? "segment-chip segment-chip-active" : "segment-chip"}
          onClick={() => onChainChange(item.value)}
        >
          {item.label}
          {item.beta ? <span>beta</span> : null}
        </button>
      ))}
    </div>
  );
}

function fromPublicProject(project: PublicProjectSummary): BuyerResult {
  return {
    chain: project.chain,
    address: project.address,
    score: project.score,
    findings: project.public_findings,
    limitations: project.limitations,
    publicHref: `/p/${project.chain}/${project.address}`
  };
}

function VerdictCard({ result, chain, address }: { result: BuyerResult | null; chain: Chain; address: string }) {
  const score = result?.score?.final_score;
  const verdict = verdictFor(score);
  const safeAddress = result?.address ?? address;
  return (
    <article className={`buyer-verdict buyer-verdict-${verdict.tone}`}>
      <div>
        <span>Вердикт wr3</span>
        <h2>{verdict.title}</h2>
        <p>{verdict.action}</p>
      </div>
      <div className="buyer-score-orb">
        <span>{score ?? "--"}</span>
        <small>{score === null || score === undefined ? "score" : "/100"}</small>
      </div>
      <footer>
        {chainLabels[result?.chain ?? chain]} · {safeAddress ? shortAddress(safeAddress) : "адрес не выбран"} · {verdict.label}
      </footer>
    </article>
  );
}

function NextActionCard({
  result,
  chain,
  address,
  onOpenBounty
}: {
  result: BuyerResult | null;
  chain: Chain;
  address: string;
  onOpenBounty: () => void;
}) {
  const verdict = verdictFor(result?.score?.final_score);
  return (
    <article className="buyer-panel">
      <div className="section-heading buyer-section-heading">
        <div>
          <p className="eyebrow">Что делать сейчас</p>
          <h2>{verdict.tone === "red" ? "Не входи без доп. проверки" : verdict.tone === "pending" ? "Сначала получи больше данных" : "Двигайся осторожно"}</h2>
        </div>
      </div>
      <div className="buyer-action-grid">
        <div>
          <ShieldAlert aria-hidden="true" size={20} />
          <strong>{verdict.action}</strong>
          <span>Это не инвестиционный совет и не гарантия безопасности.</span>
        </div>
        <Link href={`/p/${result?.chain ?? chain}/${result?.address ?? address}`}>Открыть публичную страницу</Link>
        <button type="button" className="secondary-button buyer-bounty-jump" onClick={onOpenBounty}>
          <Bug aria-hidden="true" size={17} />
          Создать bug bounty report
        </button>
      </div>
    </article>
  );
}

function ReasonsCard({ result }: { result: BuyerResult | null }) {
  const reasons = safeReasons(result);
  return (
    <article className="buyer-panel">
      <p className="eyebrow">Почему wr3 так считает</p>
      <div className="buyer-reason-list">
        {reasons.map((reason, index) => (
          <div key={`${reason}-${index}`}>
            <span>{index + 1}</span>
            <strong>{reason}</strong>
          </div>
        ))}
      </div>
    </article>
  );
}

function ShareCard({ result, chain, address }: { result: BuyerResult | null; chain: Chain; address: string }) {
  const [origin, setOrigin] = useState("");
  const publicPath = result?.publicHref ?? `/p/${chain}/${address}`;
  const publicUrl = origin ? new URL(publicPath, origin).toString() : publicPath;
  const text = shareText(result, chain, address).replace(publicPath, publicUrl);
  const telegramHref = `https://t.me/share/url?url=${encodeURIComponent(publicUrl)}&text=${encodeURIComponent(text)}`;
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  async function copyText() {
    await navigator.clipboard?.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <article className="buyer-panel buyer-share-card">
      <p className="eyebrow">Поделиться отчётом</p>
      <pre>{text}</pre>
      <div className="buyer-share-actions">
        <button type="button" className="secondary-button" onClick={copyText}>
          <Clipboard aria-hidden="true" size={17} />
          {copied ? "Скопировано" : "Скопировать текст"}
        </button>
        <a href={telegramHref} target="_blank" rel="noreferrer">
          <Send aria-hidden="true" size={17} />
          Отправить в Telegram
        </a>
      </div>
    </article>
  );
}

function TechnicalDetails({ result }: { result: BuyerResult | null }) {
  return (
    <details className="buyer-tech-details">
      <summary>Технические детали</summary>
      <div>
        <p>Этот блок спрятан, чтобы не грузить обычного пользователя.</p>
        <dl className="compact-definition-list">
          <div>
            <dt>Состояние</dt>
            <dd>{result?.audit ? auditStateLabels[result.audit.state] : "нет аудита"}</dd>
          </div>
          <div>
            <dt>Ограничения</dt>
            <dd>{result?.limitations.length ? result.limitations.slice(0, 2).map(tLimitation).join(" · ") : "нет"}</dd>
          </div>
        </dl>
        {result?.auditHref ? <Link className="artifact-link" href={result.auditHref}>Открыть приватный отчёт</Link> : null}
      </div>
    </details>
  );
}

function HighRiskFeed() {
  const [audits, setAudits] = useState<DashboardAudit[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      const [critical, high] = await Promise.all([listAudits({ severity: "critical" }), listAudits({ severity: "high" })]);
      setAudits([...critical, ...high].slice(0, 12));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Лента риска не загрузилась");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="feed-stack">
      <div className="feed-toolbar">
        <div>
          <p className="eyebrow">Высокий риск</p>
          <h2>Осторожная лента без обвинений</h2>
        </div>
        <button type="button" className="secondary-button" onClick={load}>
          <RefreshCw aria-hidden="true" size={17} />
          Обновить
        </button>
      </div>
      {error ? <p className="error-box">{error}</p> : null}
      {isLoading ? <p className="empty-state">Загружаю сигналы риска...</p> : null}
      {!isLoading && audits.length === 0 ? (
        <div className="empty-feed">
          <Siren aria-hidden="true" size={26} />
          <strong>Красных сигналов пока нет</strong>
          <span>Когда wr3 найдёт high/critical risk, он появится здесь мягкой формулировкой.</span>
        </div>
      ) : null}
      <div className="audit-feed-list">
        {audits.map((audit) => (
          <article className="audit-feed-item buyer-risk-item" key={`${audit.audit_id}-${audit.highest_severity}`}>
            <div className="audit-feed-main">
              <span>{chainLabels[audit.chain]} · {audit.highest_severity ? severityLabels[audit.highest_severity] : "риск"}</span>
              <Link href={`/p/${audit.chain}/${audit.address}`}>{audit.address ?? audit.audit_id}</Link>
              <p>wr3 видит признаки повышенного риска. Нужна дополнительная проверка перед входом.</p>
            </div>
            <div className="audit-feed-score">
              <span>оценка</span>
              <strong>{audit.score?.final_score ?? "--"}</strong>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function BugBountyFeed() {
  const [programId, setProgramId] = useState<(typeof bountyPrograms)[number]["id"]>("custom");
  const [scopeConfirmed, setScopeConfirmed] = useState(false);
  const [chain, setChain] = useState<Chain>("base");
  const [address, setAddress] = useState("0x0000000000000000000000000000000000000000");
  const [contact, setContact] = useState("security@example.org");
  const [audit, setAudit] = useState<AuditSummary | null>(null);
  const [ownerToken, setOwnerToken] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Finding[]>([]);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [checked, setChecked] = useState<string[]>([]);
  const [caseResult, setCaseResult] = useState<DisclosureCase | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isCreatingCase, setIsCreatingCase] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const addressError = useMemo(() => validateAddress(chain, address), [chain, address]);
  const program = bountyPrograms.find((item) => item.id === programId) ?? bountyPrograms[0];
  const selectedFinding = candidates.find((finding) => finding.id === selectedFindingId) ?? candidates[0] ?? null;
  const checklistComplete = checked.length === validationChecklist.length;

  async function pollAudit(auditId: string, token: string) {
    for (let attempt = 0; attempt < 10; attempt += 1) {
      const nextAudit = await getAudit(auditId, token);
      if (nextAudit.score || ["completed", "partial", "failed", "needs_source"].includes(nextAudit.state)) {
        return nextAudit;
      }
      await new Promise((resolve) => setTimeout(resolve, 800));
    }
    return getAudit(auditId, token);
  }

  async function runSafeScan() {
    setError(null);
    setCaseResult(null);
    if (!scopeConfirmed) {
      setError("Сначала подтверди scope. Без этого bounty-mode не запускает проверку.");
      return;
    }
    if (addressError) {
      setError(addressError);
      return;
    }
    setIsScanning(true);
    try {
      const created = await createAudit({
        chain,
        address,
        source: "",
        allow_bytecode_only: true,
        requested_depth: "standard",
        visibility: "private",
        user_intent: "third_party_research",
        tier: "team"
      });
      setOwnerToken(created.owner_access_token);
      const nextAudit = await pollAudit(created.audit_id, created.owner_access_token);
      const findings = await getFindings(created.audit_id, created.owner_access_token);
      const filtered = findings
        .filter((finding) => finding.severity !== "info" && finding.exploitability !== "dismissed")
        .sort((a, b) => severityRank(b.severity) - severityRank(a.severity) || b.confidence - a.confidence);
      setAudit(nextAudit);
      setCandidates(filtered);
      setSelectedFindingId(filtered[0]?.id ?? null);
      setChecked([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Safe scan не запустился");
    } finally {
      setIsScanning(false);
    }
  }

  async function openDisclosureCase() {
    if (!selectedFinding) {
      setError("Сначала выбери candidate bug.");
      return;
    }
    if (!checklistComplete) {
      setError("Перед disclosure нужно пройти manual validation checklist.");
      return;
    }
    setIsCreatingCase(true);
    setError(null);
    try {
      setCaseResult(
        await createDisclosureCase({
          finding_id: selectedFinding.id,
          project_contact: contact,
          scope_note: `${program.name}: scope confirmed locally; no mainnet active actions.`
        })
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disclosure case не создался");
    } finally {
      setIsCreatingCase(false);
    }
  }

  return (
    <div className="bounty-layout">
      <section className="bounty-left">
        <article className="buyer-check-card">
          <p className="eyebrow">Bug Bounty Mode</p>
          <h2>Ищи candidate bugs безопасно.</h2>
          <label className="buyer-address-field">
            <span>Программа / режим</span>
            <select value={programId} onChange={(event) => setProgramId(event.target.value as typeof programId)}>
              {bountyPrograms.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>
          <div className="bounty-scope-card">
            <strong>{program.badge}</strong>
            <ul>
              {program.scope.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
          <label className="checkbox-row bounty-confirm">
            <input type="checkbox" checked={scopeConfirmed} onChange={(event) => setScopeConfirmed(event.target.checked)} />
            <span>Я подтвердил scope и понимаю: никаких active mainnet действий.</span>
          </label>
        </article>

        <article className="buyer-check-card">
          <p className="eyebrow">Safe scan</p>
          <ChainPicker chain={chain} onChainChange={setChain} />
          <label className="buyer-address-field">
            <span>In-scope address</span>
            <input value={address} onChange={(event) => setAddress(event.target.value.trim())} placeholder="0x..." />
            {addressError ? <small>{addressError}</small> : null}
          </label>
          <button type="button" className="buyer-primary" disabled={isScanning || !scopeConfirmed} onClick={runSafeScan}>
            {isScanning ? <Loader2 className="spin" aria-hidden="true" size={18} /> : <Bug aria-hidden="true" size={18} />}
            Запустить safe scan
          </button>
          {error ? <p className="error-box">{error}</p> : null}
        </article>
      </section>

      <section className="bounty-right">
        <article className="buyer-panel">
          <div className="section-heading buyer-section-heading">
            <div>
              <p className="eyebrow">Candidate bugs</p>
              <h2>{candidates.length ? `${candidates.length} кандидатов` : "Кандидатов пока нет"}</h2>
            </div>
            {audit ? <span className="bounty-status-pill">{auditStateLabels[audit.state]}</span> : null}
          </div>
          <div className="bounty-candidate-list">
            {candidates.length === 0 ? (
              <p className="empty-state">Запусти safe scan. wr3 покажет потенциальные bugs без exploit-инструкций.</p>
            ) : null}
            {candidates.map((finding) => (
              <button
                type="button"
                key={finding.id}
                className={selectedFinding?.id === finding.id ? "bounty-candidate bounty-candidate-active" : "bounty-candidate"}
                onClick={() => setSelectedFindingId(finding.id)}
              >
                <span>{severityLabels[finding.severity]} · {Math.round(finding.confidence * 100)}%</span>
                <strong>{tFindingText(finding.summary)}</strong>
                <small>{finding.taxonomy.wr3_category}</small>
              </button>
            ))}
          </div>
        </article>

        <article className="buyer-panel">
          <p className="eyebrow">Manual validation checklist</p>
          <div className="bounty-checklist">
            {validationChecklist.map((item) => (
              <label className="checkbox-row" key={item}>
                <input
                  type="checkbox"
                  checked={checked.includes(item)}
                  onChange={(event) => {
                    setChecked((current) =>
                      event.target.checked ? [...current, item] : current.filter((entry) => entry !== item)
                    );
                  }}
                />
                <span>{item}</span>
              </label>
            ))}
          </div>
        </article>

        <article className="buyer-panel bounty-report-panel">
          <p className="eyebrow">Report generator</p>
          <pre>{buildBountyReport({ finding: selectedFinding, chain, address, programName: program.name, checklistComplete })}</pre>
          <div className="buyer-share-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => navigator.clipboard?.writeText(buildBountyReport({ finding: selectedFinding, chain, address, programName: program.name, checklistComplete }))}
            >
              <Clipboard aria-hidden="true" size={17} />
              Скопировать report
            </button>
            <button type="button" disabled={!selectedFinding || !checklistComplete || isCreatingCase} onClick={openDisclosureCase}>
              {isCreatingCase ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <FileText aria-hidden="true" size={17} />}
              Создать disclosure case
            </button>
          </div>
          {caseResult ? (
            <p className="empty-state">Disclosure case создан: {caseResult.id}. Следующий дедлайн: {new Date(caseResult.deadline_next).toLocaleDateString("ru-RU")}.</p>
          ) : null}
        </article>
      </section>
    </div>
  );
}

function BuyerAlertsFeed() {
  const [chain, setChain] = useState<Chain>("base");
  const [address, setAddress] = useState("0x0000000000000000000000000000000000000000");
  const [response, setResponse] = useState<TelegramEmulatorResponse | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const addressError = useMemo(() => validateAddress(chain, address), [chain, address]);

  async function watch() {
    setError(null);
    if (addressError) {
      setError(addressError);
      return;
    }
    setIsBusy(true);
    try {
      setResponse(await telegramEmulatorCommand(`/watch ${chain} ${address} buyer-alert`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Алерт не включился");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <div className="buyer-check-layout">
      <section className="buyer-check-card">
        <p className="eyebrow">Мои алерты</p>
        <h2>Следи за токеном без шума.</h2>
        <ChainPicker chain={chain} onChainChange={setChain} />
        <label className="buyer-address-field">
          <span>Адрес токена</span>
          <input value={address} onChange={(event) => setAddress(event.target.value.trim())} />
          {addressError ? <small>{addressError}</small> : null}
        </label>
        <button type="button" className="buyer-primary" disabled={isBusy} onClick={watch}>
          {isBusy ? <Loader2 className="spin" aria-hidden="true" size={18} /> : <Bell aria-hidden="true" size={18} />}
          Включить алерты
        </button>
        {error ? <p className="error-box">{error}</p> : null}
      </section>
      <section className="buyer-result-stack">
        <article className="buyer-panel">
          <p className="eyebrow">Статус</p>
          <h2>{response?.ok ? "Алерт включён" : "Алерт пока не включён"}</h2>
          <p className="muted-copy">
            {response?.reply ?? "wr3 будет полезен, когда у токена изменится риск, появится новый сигнал или потребуется повторная проверка."}
          </p>
        </article>
      </section>
    </div>
  );
}

function ExplainersFeed() {
  return (
    <div className="feed-stack">
      <div className="feed-toolbar">
        <div>
          <p className="eyebrow">Простыми словами</p>
          <h2>Мини-словарь риска для покупателя токена</h2>
        </div>
      </div>
      <div className="explainer-grid">
        {explainers.map((item) => (
          <article className="explainer-card" key={item.title}>
            <TriangleAlert aria-hidden="true" size={20} />
            <span>{item.title}</span>
            <strong>{item.short}</strong>
            <p>{item.detail}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function EngineReadinessFeed() {
  const [status, setStatus] = useState<ToolsStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      setStatus(await getToolsStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не получилось проверить локальные инструменты");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const requiredReady = status ? `${status.required_installed}/${status.required_total}` : "--";
  const optionalMissing = status?.optional_missing.length ?? 0;

  return (
    <div className="feed-stack engine-feed">
      <div className="feed-toolbar">
        <div>
          <p className="eyebrow">Готовность движка</p>
          <h2>Что реально работает на MacBook</h2>
        </div>
        <button type="button" className="secondary-button" onClick={load}>
          <RefreshCw aria-hidden="true" size={17} />
          Проверить
        </button>
      </div>

      {error ? <p className="error-box">{error}</p> : null}
      {isLoading ? <p className="empty-state">Проверяю локальные tools...</p> : null}

      <div className="engine-metrics">
        <article>
          <span>Обязательные</span>
          <strong>{requiredReady}</strong>
          <p>{status?.status === "ready" ? "Готово для localhost" : "Нужна установка"}</p>
        </article>
        <article>
          <span>Всего найдено</span>
          <strong>{status?.installed_total ?? "--"}</strong>
          <p>Foundry, Slither, Aderyn, Wake, Medusa, Trident и другие.</p>
        </article>
        <article>
          <span>Optional missing</span>
          <strong>{optionalMissing}</strong>
          <p>ItyFuzz может быть optional: skipped artifact вместо фейка.</p>
        </article>
      </div>

      <div className="engine-tool-list">
        {status?.tools.map((tool) => (
          <article className={tool.installed ? "engine-tool engine-tool-ok" : "engine-tool"} key={tool.id}>
            <div>
              <span>{tool.category}</span>
              <strong>{tool.label}</strong>
              <p>{tool.safe_scope}</p>
            </div>
            <b>{tool.installed ? "ok" : tool.required_for_local_100 ? "нужно" : "optional"}</b>
          </article>
        ))}
      </div>

      <div className="engine-links">
        <Link href="/tools">Открыть полную страницу tools</Link>
        <Link href="/integrations">Статус API и бесплатных fallback</Link>
        <Link href="/dashboard">Dev/security dashboard</Link>
      </div>
    </div>
  );
}

function shortAddress(address: string) {
  if (address.length <= 16) return address;
  return `${address.slice(0, 8)}...${address.slice(-6)}`;
}

function severityRank(severity: Finding["severity"]) {
  const ranks: Record<Finding["severity"], number> = {
    critical: 5,
    high: 4,
    medium: 3,
    low: 2,
    info: 1
  };
  return ranks[severity];
}

function buildBountyReport({
  finding,
  chain,
  address,
  programName,
  checklistComplete
}: {
  finding: Finding | null;
  chain: Chain;
  address: string;
  programName: string;
  checklistComplete: boolean;
}) {
  if (!finding) {
    return `# Bug bounty report draft

Status: candidate not selected
Program: ${programName}
Target: ${chain}:${address}

Next:
- Run safe scan.
- Select a candidate bug.
- Complete manual validation checklist.
- Write reproduction using local fork/testnet only.`;
  }

  return `# ${tFindingText(finding.summary)}

Program: ${programName}
Target: ${chain}:${address}
Severity candidate: ${severityLabels[finding.severity]}
Confidence: ${Math.round(finding.confidence * 100)}%
Manual validation: ${checklistComplete ? "completed" : "not completed"}

## Summary
${tFindingText(finding.description)}

## Impact
${tFindingText(finding.impact)}

## Evidence
- Source: ${finding.sources.join(", ")}
- Category: ${finding.taxonomy.wr3_category}
- Location: ${finding.location.file ?? "unknown"}:${finding.location.start_line ?? "?"}

## Reproduction
Local/fork/testnet only. Do not broadcast mainnet transactions.
TODO: add minimal reproducible steps after manual validation.

## Recommendation
${tFindingText(finding.recommendation)}

## Safety notes
- No active mainnet actions were performed.
- No funds were moved.
- Report should be sent privately through the official program channel.`;
}
