"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  BellRing,
  BookOpenCheck,
  Bug,
  CheckCircle2,
  ClipboardList,
  Cpu,
  FileText,
  Gauge,
  Loader2,
  NotebookPen,
  Play,
  Radar,
  RefreshCw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Siren,
  UserCheck,
  XCircle
} from "lucide-react";
import type { AuditState, Chain, Severity, Tier } from "@wr3/shared";
import {
  appendDisclosureContact,
  createAudit,
  createDisclosureCase,
  getToolsStatus,
  listAudits,
  listDisclosureCases,
  type DashboardAudit,
  type DisclosureCase,
  type ToolsStatusResponse
} from "@/lib/api";
import { auditStateLabels, chainLabels, severityLabels, tierLabels } from "@/lib/i18n";

type TaskStatus =
  | "candidate"
  | "needs_validation"
  | "reproducing"
  | "validated"
  | "report_draft"
  | "submitted"
  | "dismissed"
  | "blocked";

type TaskOverride = {
  status?: TaskStatus;
  assignee?: string;
  note?: string;
  supportContact?: string;
  disclosureCaseId?: string;
};

type FindingTask = {
  id: string;
  audit: DashboardAudit;
  title: string;
  status: TaskStatus;
  severity: Severity | "none";
  assignee: string;
  note: string;
  legalGate: "clear" | "review" | "blocked";
  nextStep: string;
};

type CockpitTab = "scan" | "findings" | "disclosure" | "engine" | "links";

const cockpitTabs: { id: CockpitTab; label: string; description: string; icon: LucideIcon }[] = [
  { id: "scan", label: "Скан", description: "адрес или код", icon: Radar },
  { id: "findings", label: "Очередь багов", description: "проверка кандидатов", icon: Bug },
  { id: "disclosure", label: "Обращение", description: "канал и отчёт", icon: Send },
  { id: "engine", label: "Движок", description: "инструменты и здоровье", icon: Cpu },
  { id: "links", label: "Рабочие ссылки", description: "быстрый доступ", icon: ClipboardList }
];

const localTaskKey = "wr3-command-center-task-overrides-v1";
const teamMembers = ["Егор", "Исследователь", "Юрист", "Не назначено"];

const statusLabels: Record<TaskStatus, string> = {
  candidate: "Кандидат",
  needs_validation: "Проверить",
  reproducing: "Воспроизвести",
  validated: "Подтверждено",
  report_draft: "Черновик отчёта",
  submitted: "Отправлено",
  dismissed: "Отклонено",
  blocked: "Блокер"
};

const statusNext: Record<TaskStatus, string> = {
  candidate: "Разобрать сигнал и подтвердить правила программы.",
  needs_validation: "Проверить вручную и убрать ложное срабатывание.",
  reproducing: "Запустить безопасное local/fork/test воспроизведение.",
  validated: "Собрать черновик отчёта.",
  report_draft: "Проверить формулировки и отправить приватно.",
  submitted: "Ждать ответа и вести повторный контакт.",
  dismissed: "Оставить причину отклонения в заметках.",
  blocked: "Снять блокер или отложить задачу."
};

const severityOrder: Record<Severity | "none", number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
  none: 0
};

const defaultSource = `contract Vault {
    address public owner;
    uint256 public totalShares;

    function withdraw(uint256 shares) external {
        require(tx.origin == msg.sender, "blocked");
        totalShares -= shares;
        payable(msg.sender).transfer(shares);
    }
}`;

const realTargets: { label: string; chain: Chain; address: string }[] = [
  { label: "Base USDC", chain: "base", address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" },
  { label: "ETH USDC", chain: "ethereum", address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" },
  { label: "ARB USDC", chain: "arbitrum", address: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831" },
  { label: "BSC USDT", chain: "bsc", address: "0x55d398326f99059fF775485246999027B3197955" }
];

const chains: { value: Chain; label: string; beta?: boolean }[] = [
  { value: "base", label: "Base" },
  { value: "ethereum", label: "ETH" },
  { value: "bsc", label: "BSC" },
  { value: "arbitrum", label: "ARB" },
  { value: "solana", label: "Solana", beta: true }
];

const depths: { value: "preliminary" | "standard" | "deep"; label: string }[] = [
  { value: "preliminary", label: "Быстро" },
  { value: "standard", label: "Стандарт" },
  { value: "deep", label: "Глубоко" }
];

function defaultTaskStatus(audit: DashboardAudit): TaskStatus {
  if (audit.state === "failed") return "blocked";
  if (audit.highest_severity === "critical" || audit.highest_severity === "high") return "needs_validation";
  if (audit.finding_count > 0) return "candidate";
  if (audit.state === "needs_source") return "blocked";
  return "candidate";
}

function taskTitle(audit: DashboardAudit) {
  const severity = audit.highest_severity ? severityLabels[audit.highest_severity] : "кандидат";
  const address = audit.address ? shortAddress(audit.address) : shortAddress(audit.audit_id);
  return `${severity} · ${chainLabels[audit.chain]} · ${address}`;
}

function loadOverrides(): Record<string, TaskOverride> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(localTaskKey);
    return raw ? (JSON.parse(raw) as Record<string, TaskOverride>) : {};
  } catch {
    return {};
  }
}

function saveOverrides(overrides: Record<string, TaskOverride>) {
  window.localStorage.setItem(localTaskKey, JSON.stringify(overrides));
}

function shortAddress(value: string) {
  if (value.length <= 16) return value;
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

function healthPercent(status: ToolsStatusResponse | null) {
  if (!status || status.required_total === 0) return 0;
  return Math.round((status.required_installed / status.required_total) * 100);
}

function legalGateFor(task: FindingTask): "clear" | "review" | "blocked" {
  if (task.status === "dismissed") return "clear";
  if (task.status === "blocked" || task.audit.state === "failed") return "blocked";
  if (task.severity === "critical" || task.severity === "high" || task.status === "report_draft") return "review";
  return "clear";
}

function legalGateLabel(gate: FindingTask["legalGate"]) {
  if (gate === "clear") return "чисто";
  if (gate === "review") return "review";
  return "блокер";
}

function buildTasks(audits: DashboardAudit[], overrides: Record<string, TaskOverride>): FindingTask[] {
  return audits
    .map((audit) => {
      const override = overrides[audit.audit_id] ?? {};
      const status = override.status ?? defaultTaskStatus(audit);
      const task: FindingTask = {
        id: audit.audit_id,
        audit,
        title: taskTitle(audit),
        status,
        severity: audit.highest_severity ?? "none",
        assignee: override.assignee ?? "Не назначено",
        note: override.note ?? "",
        legalGate: "clear",
        nextStep: statusNext[status]
      };
      task.legalGate = legalGateFor(task);
      return task;
    })
    .sort((a, b) => {
      if (a.status === "dismissed" && b.status !== "dismissed") return 1;
      if (b.status === "dismissed" && a.status !== "dismissed") return -1;
      return severityOrder[b.severity] - severityOrder[a.severity];
    });
}

export function InternalCommandCenter() {
  const [audits, setAudits] = useState<DashboardAudit[]>([]);
  const [disclosures, setDisclosures] = useState<DisclosureCase[]>([]);
  const [toolsStatus, setToolsStatus] = useState<ToolsStatusResponse | null>(null);
  const [overrides, setOverrides] = useState<Record<string, TaskOverride>>({});
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<CockpitTab>("scan");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const tasks = useMemo(() => buildTasks(audits, overrides), [audits, overrides]);
  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0] ?? null;
  const engineHealth = healthPercent(toolsStatus);

  const metrics = useMemo(() => {
    const highCriticalWaiting = tasks.filter(
      (task) =>
        (task.severity === "critical" || task.severity === "high") &&
        !["dismissed", "submitted"].includes(task.status)
    ).length;
    return {
      highCriticalWaiting,
      reportsReady: tasks.filter((task) => task.status === "report_draft").length,
      disclosureDeadlines: disclosures.length,
      engineHealth,
      failedScans: audits.filter((audit) => audit.state === "failed").length,
      openTasks: tasks.filter((task) => !["dismissed", "submitted"].includes(task.status)).length,
      legalBlockers: tasks.filter((task) => task.legalGate !== "clear").length
    };
  }, [audits, disclosures.length, engineHealth, tasks]);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      const [auditRows, toolRows, disclosureRows] = await Promise.all([
        listAudits(),
        getToolsStatus(),
        listDisclosureCases()
      ]);
      setAudits(auditRows);
      setToolsStatus(toolRows);
      setDisclosures(disclosureRows);
      setOverrides(loadOverrides());
      setSelectedTaskId((current) => current ?? auditRows[0]?.audit_id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Рабочий центр не загрузился");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function patchTask(taskId: string, patch: TaskOverride) {
    const next = {
      ...overrides,
      [taskId]: {
        ...(overrides[taskId] ?? {}),
        ...patch
      }
    };
    setOverrides(next);
    saveOverrides(next);
  }

  const tabCounters: Record<CockpitTab, string | number> = {
    scan: "старт",
    findings: metrics.openTasks,
    disclosure: metrics.legalBlockers,
    engine: `${engineHealth}%`,
    links: "далее"
  };

  return (
    <section className="command-center" aria-label="внутренний рабочий центр wr3">
      <header className="cockpit-hero">
        <div>
          <div className="hero-badge cockpit-badge">
            <Radar aria-hidden="true" size={17} />
            <span>wr3 · локальная рабочая платформа</span>
          </div>
          <h1>Проверка контрактов и багов.</h1>
        </div>
        <div className="cockpit-mission-card" aria-label="Фокус дня">
          <span>Сегодняшний фокус</span>
          <strong>{metrics.highCriticalWaiting ? "Закрыть очередь проверки" : "Найти новый кандидатный баг"}</strong>
          <p>{metrics.openTasks} открытых задач · {metrics.legalBlockers} юридических проверок · движок {engineHealth}%</p>
        </div>
      </header>

      <section className="cockpit-tabs" aria-label="Верхние вкладки wr3">
        {cockpitTabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              type="button"
              key={tab.id}
              className={activeTab === tab.id ? "cockpit-tab cockpit-tab-active" : "cockpit-tab"}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon aria-hidden="true" size={18} />
              <span>{tab.label}</span>
              <small>{tab.description}</small>
              <b>{tabCounters[tab.id]}</b>
            </button>
          );
        })}
      </section>

      {error ? <p className="error-box">{error}</p> : null}

      <section className="cockpit-tab-shell" aria-live="polite">
        {activeTab === "scan" ? (
          <div className="cockpit-tab-grid cockpit-tab-grid-scan">
            <div className="cockpit-tab-column">
              <QuickScanPanel />
            </div>
            <div className="cockpit-tab-column">
              <ScanGuidePanel metrics={metrics} />
              <SafetyWorkflowPanel />
            </div>
          </div>
        ) : null}

        {activeTab === "findings" ? (
          <div className="cockpit-tab-grid cockpit-tab-grid-wide cockpit-tab-grid-findings">
            <div className="cockpit-tab-column">
              <FindingsQueue
                isLoading={isLoading}
                tasks={tasks}
                selectedTask={selectedTask}
                onRefresh={load}
                onSelect={(task) => setSelectedTaskId(task.id)}
              />
            </div>
            <div className="cockpit-tab-column">
              <TaskDetail task={selectedTask} onPatch={patchTask} />
              <SafetyWorkflowPanel />
            </div>
          </div>
        ) : null}

        {activeTab === "disclosure" ? (
          <div className="cockpit-tab-grid cockpit-tab-grid-wide">
            <div className="cockpit-tab-column">
              <SupportRoutePanel task={selectedTask} />
              <LegalPanel tasks={tasks} disclosures={disclosures} />
              <SafetyWorkflowPanel />
              <QuickLinksPanel />
            </div>
            <div className="cockpit-tab-column">
              <TaskDetail task={selectedTask} onPatch={patchTask} />
            </div>
          </div>
        ) : null}

        {activeTab === "engine" ? (
          <div className="cockpit-tab-grid cockpit-tab-grid-engine">
            <div className="cockpit-tab-column">
              <EngineHealth status={toolsStatus} />
              <MetricsPanel metrics={metrics} />
            </div>
            <div className="cockpit-tab-column">
              <BountyRadar tasks={tasks} />
              <SafetyWorkflowPanel />
              <QuickLinksPanel />
            </div>
          </div>
        ) : null}

        {activeTab === "links" ? (
          <div className="cockpit-tab-grid cockpit-tab-grid-links">
            <div className="cockpit-tab-column">
              <QuickLinksPanel />
            </div>
            <div className="cockpit-tab-column">
              <SafetyWorkflowPanel />
            </div>
          </div>
        ) : null}
      </section>
    </section>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  tone
}: {
  icon: typeof ShieldAlert;
  label: string;
  value: string | number;
  tone: "red" | "yellow" | "green" | "blue";
}) {
  return (
    <article className={`cockpit-metric cockpit-metric-${tone}`}>
      <Icon aria-hidden="true" size={19} />
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function ScanGuidePanel({
  metrics
}: {
  metrics: {
    highCriticalWaiting: number;
    reportsReady: number;
    disclosureDeadlines: number;
    engineHealth: number;
    failedScans: number;
    openTasks: number;
    legalBlockers: number;
  };
}) {
  return (
    <section className="cockpit-panel cockpit-feed-panel">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Что будет после скана</p>
          <h2>Одна задача вместо перегруза</h2>
        </div>
        <Radar aria-hidden="true" size={24} />
      </div>
      <div className="workflow-feed">
        <div>
          <b>1</b>
          <span>wr3 получает source или делает bytecode-only limited scan.</span>
        </div>
        <div>
          <b>2</b>
          <span>Подозрительные сигналы попадают во вкладку “Очередь багов”.</span>
        </div>
        <div>
          <b>3</b>
          <span>Во вкладке “Обращение” ты собираешь безопасное письмо в support/security.</span>
        </div>
      </div>
      <div className="cockpit-mini-metrics" aria-label="Короткая сводка">
        <div><span>Открытые задачи</span><strong>{metrics.openTasks}</strong></div>
        <div><span>High/Critical</span><strong>{metrics.highCriticalWaiting}</strong></div>
        <div><span>Готовность движка</span><strong>{metrics.engineHealth}%</strong></div>
        <div><span>Юр. проверки</span><strong>{metrics.legalBlockers}</strong></div>
      </div>
    </section>
  );
}

function MetricsPanel({
  metrics
}: {
  metrics: {
    highCriticalWaiting: number;
    reportsReady: number;
    disclosureDeadlines: number;
    engineHealth: number;
    failedScans: number;
    openTasks: number;
    legalBlockers: number;
  };
}) {
  return (
    <section className="cockpit-metrics cockpit-metrics-tab" aria-label="Метрики Command Center">
      <MetricCard icon={ShieldAlert} label="High/Critical на проверке" value={metrics.highCriticalWaiting} tone="red" />
      <MetricCard icon={FileText} label="Отчёты готовы" value={metrics.reportsReady} tone="blue" />
      <MetricCard icon={BellRing} label="Сроки disclosure" value={metrics.disclosureDeadlines} tone="yellow" />
      <MetricCard icon={Gauge} label="Здоровье движка" value={`${metrics.engineHealth}%`} tone="green" />
      <MetricCard icon={XCircle} label="Упавшие сканы" value={metrics.failedScans} tone="red" />
      <MetricCard icon={ClipboardList} label="Открытые задачи" value={metrics.openTasks} tone="blue" />
      <MetricCard icon={BookOpenCheck} label="Юр. блокеры" value={metrics.legalBlockers} tone="yellow" />
    </section>
  );
}

function SupportRoutePanel({ task }: { task: FindingTask | null }) {
  const target = task?.audit.address ?? task?.audit.audit_id ?? "цель не выбрана";
  const chain = task ? chainLabels[task.audit.chain] : "сеть не выбрана";

  return (
    <section className="cockpit-panel support-route-panel">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Куда писать в поддержку</p>
          <h2>Сначала официальный канал, потом репорт</h2>
        </div>
        <Send aria-hidden="true" size={24} />
      </div>
      <div className="support-target-card">
        <span>Текущая цель</span>
        <strong>{chain} · {shortAddress(target)}</strong>
        <p>wr3 не выдумывает support email. Контакт нужно подтвердить по официальным источникам проекта.</p>
      </div>
      <div className="support-route-list">
        <div><b>1</b><span>Официальный сайт проекта: раздел Security, Contact, Docs или Bug bounty.</span></div>
        <div><b>2</b><span>GitHub репозиторий: вкладка Security policy или SECURITY.md.</span></div>
        <div><b>3</b><span>Immunefi, Hats, Code4rena, Sherlock, Cantina: только если программа реально in-scope.</span></div>
        <div><b>4</b><span>Официальный Discord/TG: проси security contact, но не публикуй PoC и детали бага.</span></div>
      </div>
      <p className="cockpit-safety-note">
        Правило wr3: сначала ручная проверка и приватный канал. Никаких публичных “скам/взлом” заявлений и mainnet-действий.
      </p>
    </section>
  );
}

function QuickScanPanel() {
  const router = useRouter();
  const [chain, setChain] = useState<Chain>("base");
  const [address, setAddress] = useState("0x0000000000000000000000000000000000000000");
  const [source, setSource] = useState(defaultSource);
  const [inputMode, setInputMode] = useState<"real_address" | "pasted_source">("real_address");
  const [depth, setDepth] = useState<"preliminary" | "standard" | "deep">("standard");
  const [tier, setTier] = useState<Tier>("team");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedTier = window.localStorage.getItem("wr3-local-tier") as Tier | null;
    if (storedTier && ["free", "hobby", "team", "pro"].includes(storedTier)) {
      setTier(storedTier);
    }
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await createAudit({
        chain,
        address,
        source: inputMode === "pasted_source" ? source : "",
        allow_bytecode_only: true,
        requested_depth: depth,
        visibility: "private",
        user_intent: "pre_launch_self_check",
        tier
      });
      router.push(`/audits/${response.audit_id}?owner_token=${encodeURIComponent(response.owner_access_token)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Скан не запустился");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="cockpit-panel cockpit-quick-scan" onSubmit={submit}>
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Быстрый скан</p>
          <h2>Реальный контракт → задача по багу.</h2>
        </div>
        <Cpu aria-hidden="true" size={25} />
      </div>

      <div className="cockpit-control-row" aria-label="Сеть">
        {chains.map((item) => (
          <button
            type="button"
            key={item.value}
            className={chain === item.value ? "cockpit-chip cockpit-chip-active" : "cockpit-chip"}
            onClick={() => setChain(item.value)}
          >
            {item.label}
            {item.beta ? <span>beta</span> : null}
          </button>
        ))}
      </div>

      <div className="cockpit-control-row" aria-label="Режим входных данных">
        <button
          type="button"
          className={inputMode === "real_address" ? "cockpit-chip cockpit-chip-active" : "cockpit-chip"}
          onClick={() => setInputMode("real_address")}
        >
          Реальный адрес
        </button>
        <button
          type="button"
          className={inputMode === "pasted_source" ? "cockpit-chip cockpit-chip-active" : "cockpit-chip"}
          onClick={() => setInputMode("pasted_source")}
        >
          Вставить код
        </button>
      </div>

      <div className="real-target-row" aria-label="Реальные адреса для проверки">
        {realTargets.map((target) => (
          <button
            type="button"
            className="secondary-button"
            key={target.label}
            onClick={() => {
              setChain(target.chain);
              setAddress(target.address);
              setInputMode("real_address");
            }}
          >
            {target.label}
          </button>
        ))}
      </div>

      <div className="cockpit-two-col">
        <label>
          Адрес / ID программы
          <input value={address} onChange={(event) => setAddress(event.target.value.trim())} placeholder="0x..." />
        </label>
        <label>
          Режим
          <select value={depth} onChange={(event) => setDepth(event.target.value as typeof depth)}>
            {depths.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
      </div>

      {inputMode === "pasted_source" ? (
        <label>
          Исходный код / заметки для локального скана
          <textarea rows={7} value={source} onChange={(event) => setSource(event.target.value)} />
        </label>
      ) : (
        <article className="real-address-note">
          <strong>Режим реального адреса</strong>
          <span>
            wr3 попробует получить verified source через explorer keys, затем включит bytecode-only limited scan.
            Если исходный код недоступен, задача попадёт в очередь как ограниченный сигнал, а не fake exploit.
          </span>
        </article>
      )}

      <div className="cockpit-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={() => {
            setInputMode("pasted_source");
            setSource(defaultSource);
          }}
        >
          <NotebookPen aria-hidden="true" size={17} />
          Демо-код
        </button>
        <button type="submit" disabled={isSubmitting || (!address && !source)}>
          {isSubmitting ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <Play aria-hidden="true" size={17} />}
          Запустить скан
        </button>
      </div>
      <p className="cockpit-safety-note">Только passive/local/fork/test. Никаких mainnet-транзакций, broadcast и публичных обвинений.</p>
      {error ? <p className="error-box">{error}</p> : null}
    </form>
  );
}

function FindingsQueue({
  isLoading,
  tasks,
  selectedTask,
  onRefresh,
  onSelect
}: {
  isLoading: boolean;
  tasks: FindingTask[];
  selectedTask: FindingTask | null;
  onRefresh: () => Promise<void>;
  onSelect: (task: FindingTask) => void;
}) {
  return (
    <section className="cockpit-panel cockpit-queue">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Очередь находок</p>
          <h2>Кандидатные баги → задачи</h2>
        </div>
        <button type="button" className="secondary-button" onClick={() => void onRefresh()}>
          <RefreshCw aria-hidden="true" size={16} />
          Обновить
        </button>
      </div>

      <div className="queue-lanes" aria-label="Жизненный цикл находки">
        {["candidate", "needs_validation", "reproducing", "report_draft", "submitted"].map((status) => (
          <span key={status}>{statusLabels[status as TaskStatus]}</span>
        ))}
      </div>

      {isLoading ? <p className="empty-state">Загружаю локальную очередь...</p> : null}
      {!isLoading && tasks.length === 0 ? (
        <p className="empty-state">Очередь пустая. Запусти скан сверху, чтобы создать первую задачу.</p>
      ) : null}

      <div className="finding-task-list">
        {tasks.map((task) => (
          <button
            type="button"
            key={task.id}
            className={selectedTask?.id === task.id ? "finding-task finding-task-active" : "finding-task"}
            onClick={() => onSelect(task)}
          >
            <span className={`task-severity task-severity-${task.severity}`}>{task.severity === "none" ? "аудит" : severityLabels[task.severity]}</span>
            <strong>{task.title}</strong>
            <small>{statusLabels[task.status]} · {task.assignee}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

function TaskDetail({
  task,
  onPatch
}: {
  task: FindingTask | null;
  onPatch: (taskId: string, patch: TaskOverride) => void;
}) {
  const [draftNote, setDraftNote] = useState("");
  const [supportContact, setSupportContact] = useState("security@example.org");
  const [caseStatus, setCaseStatus] = useState<string | null>(null);
  const [caseError, setCaseError] = useState<string | null>(null);
  const [isCreatingCase, setIsCreatingCase] = useState(false);

  useEffect(() => {
    setDraftNote(task?.note ?? "");
    setSupportContact(task?.audit.chain ? `security@${chainLabels[task.audit.chain].toLowerCase()}.example.org` : "security@example.org");
    setCaseStatus(null);
    setCaseError(null);
  }, [task?.id, task?.note, task?.audit.chain]);

  if (!task) {
    return (
      <section className="cockpit-panel cockpit-detail">
        <p className="eyebrow">Карточка задачи</p>
        <h2>Выбери находку или задачу</h2>
        <p className="muted-copy">После выбора появятся проверка, воспроизведение, отчёт, отклонение, ответственный и заметки.</p>
      </section>
    );
  }

  const activeTask = task;
  const href = `/audits/${activeTask.audit.audit_id}${
    activeTask.audit.owner_access_token ? `?owner_token=${encodeURIComponent(activeTask.audit.owner_access_token)}` : ""
  }`;
  const supportDraft = buildSupportDraft(activeTask, supportContact);

  async function createSupportCase() {
    setCaseError(null);
    setIsCreatingCase(true);
    try {
      const created = await createDisclosureCase({
        finding_id: activeTask.id,
        project_contact: supportContact,
        scope_note: `Внутренняя кандидатная задача wr3. ${activeTask.nextStep} Без активных mainnet-действий.`
      });
      await appendDisclosureContact(created.id, {
        channel: "draft",
        message: supportDraft
      });
      onPatch(activeTask.id, { status: "report_draft", supportContact, disclosureCaseId: created.id });
      setCaseStatus(`Черновик disclosure case создан: ${created.id}`);
    } catch (err) {
      setCaseError(err instanceof Error ? err.message : "Черновик disclosure не создался");
    } finally {
      setIsCreatingCase(false);
    }
  }

  return (
    <section className="cockpit-panel cockpit-detail">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Карточка задачи</p>
          <h2>{task.title}</h2>
        </div>
        <span className={`legal-gate legal-gate-${task.legalGate}`}>{legalGateLabel(task.legalGate)}</span>
      </div>

      <dl className="cockpit-detail-grid">
        <div>
          <dt>Аудит</dt>
          <dd><Link href={href}>{shortAddress(task.audit.audit_id)}</Link></dd>
        </div>
        <div>
          <dt>Состояние</dt>
          <dd>{auditStateLabels[task.audit.state as AuditState]}</dd>
        </div>
        <div>
          <dt>Тариф</dt>
          <dd>{tierLabels[task.audit.tier]}</dd>
        </div>
        <div>
          <dt>Находки</dt>
          <dd>{task.audit.finding_count}</dd>
        </div>
      </dl>

      <div className="task-action-grid">
        <button type="button" onClick={() => onPatch(task.id, { status: "validated" })}>
          <CheckCircle2 aria-hidden="true" size={16} />
          Проверено
        </button>
        <button type="button" className="secondary-button" onClick={() => onPatch(task.id, { status: "reproducing" })}>
          <Play aria-hidden="true" size={16} />
          Запустить PoC
        </button>
        <button type="button" className="secondary-button" onClick={() => onPatch(task.id, { status: "report_draft" })}>
          <FileText aria-hidden="true" size={16} />
          Создать отчёт
        </button>
        <button type="button" className="secondary-button danger-button" onClick={() => onPatch(task.id, { status: "dismissed" })}>
          <XCircle aria-hidden="true" size={16} />
          Отклонить FP
        </button>
        <button type="button" className="secondary-button" onClick={createSupportCase} disabled={isCreatingCase}>
          {isCreatingCase ? <Loader2 className="spin" aria-hidden="true" size={16} /> : <Send aria-hidden="true" size={16} />}
          Черновик письма
        </button>
      </div>

      <label>
        Ответственный
        <select value={task.assignee} onChange={(event) => onPatch(task.id, { assignee: event.target.value })}>
          {teamMembers.map((member) => <option key={member} value={member}>{member}</option>)}
        </select>
      </label>

      <label>
        Контакт security/support
        <input value={supportContact} onChange={(event) => setSupportContact(event.target.value.trim())} placeholder="security@example.org" />
      </label>

      <label>
        Заметки / доказательства
        <textarea rows={5} value={draftNote} onChange={(event) => setDraftNote(event.target.value)} />
      </label>

      <div className="cockpit-actions">
        <button type="button" className="secondary-button" onClick={() => onPatch(task.id, { note: draftNote })}>
          <NotebookPen aria-hidden="true" size={16} />
          Сохранить доказательства
        </button>
        <Link className="artifact-link" href={href}>Открыть полный отчёт</Link>
      </div>

      <article className="report-draft-box">
        <span>Черновик баг-репорта</span>
        <pre>{`Название: ${task.title}
Статус: ${statusLabels[task.status]}
Scope: ${chainLabels[task.audit.chain]}:${task.audit.address ?? task.audit.audit_id}
Безопасность: только local/fork/test, без mainnet-действий.
Следующий шаг: ${task.nextStep}
Заметка/доказательства: ${task.note || "TODO"}`}</pre>
      </article>

      <article className="support-draft-box">
        <span>Черновик приватного письма</span>
        <pre>{supportDraft}</pre>
        <p>wr3 не отправляет это автоматически. Сначала ручная проверка, потом приватная отправка в официальный канал проекта.</p>
        {caseStatus ? <p className="empty-state">{caseStatus}</p> : null}
        {caseError ? <p className="error-box">{caseError}</p> : null}
      </article>
    </section>
  );
}

function BountyRadar({ tasks }: { tasks: FindingTask[] }) {
  const ready = tasks.filter((task) => ["validated", "report_draft"].includes(task.status)).length;
  const validation = tasks.filter((task) => task.status === "needs_validation").length;

  return (
    <section className="cockpit-panel bounty-radar">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Радар bug bounty</p>
          <h2>Где сейчас может быть ценность</h2>
        </div>
        <Bug aria-hidden="true" size={24} />
      </div>
      <div className="radar-board" aria-label="Радар bug bounty">
        <span className="radar-dot radar-dot-hot" />
        <span className="radar-dot radar-dot-mid" />
        <span className="radar-dot radar-dot-calm" />
        <strong>{ready}</strong>
        <small>готово к отчёту</small>
      </div>
      <div className="radar-list">
        <div><span>Тренировка / локальные примеры</span><b>безопасно</b></div>
        <div><span>Разрешённые программы</span><b>{validation} проверить</b></div>
        <div><span>Scope Safe Harbor</span><b>юр. review</b></div>
      </div>
    </section>
  );
}

function EngineHealth({ status }: { status: ToolsStatusResponse | null }) {
  const percent = healthPercent(status);
  return (
    <section className="cockpit-panel engine-health-card">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Здоровье движка</p>
          <h2>{percent}% готовность localhost</h2>
        </div>
        <Activity aria-hidden="true" size={24} />
      </div>
      <div className="engine-health-meter"><span style={{ width: `${percent}%` }} /></div>
      <div className="engine-health-grid">
        <div><span>Обязательные tools</span><strong>{status ? `${status.required_installed}/${status.required_total}` : "--"}</strong></div>
        <div><span>Установлено</span><strong>{status?.installed_total ?? "--"}</strong></div>
        <div><span>Optional отсутствует</span><strong>{status?.optional_missing.length ?? "--"}</strong></div>
      </div>
      <Link className="artifact-link" href="/tools">Открыть лабораторию движка</Link>
    </section>
  );
}

function LegalPanel({ tasks, disclosures }: { tasks: FindingTask[]; disclosures: DisclosureCase[] }) {
  const reviewTasks = tasks.filter((task) => task.legalGate !== "clear");
  return (
    <section className="cockpit-panel legal-panel-card">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Юридические проверки</p>
          <h2>{reviewTasks.length ? "Проверить формулировки" : "Нет блокеров"}</h2>
        </div>
        <Siren aria-hidden="true" size={24} />
      </div>
      <div className="legal-check-list">
        <div>
          <AlertTriangle aria-hidden="true" size={17} />
          <span>Без публичных scam/fraud обвинений</span>
        </div>
        <div>
          <ShieldCheck aria-hidden="true" size={17} />
          <span>Без активных mainnet-действий вне scope</span>
        </div>
        <div>
          <UserCheck aria-hidden="true" size={17} />
          <span>Ручная проверка перед публичными High/Critical заявлениями</span>
        </div>
      </div>
      <p className="muted-copy">{disclosures.length} disclosure-кейса в локальном трекере.</p>
      <Link className="artifact-link" href="/disclosure">Открыть disclosure-панель</Link>
    </section>
  );
}

function SafetyWorkflowPanel() {
  return (
    <section className="cockpit-panel cockpit-helper-card">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Рабочий порядок</p>
          <h2>Как довести находку до результата</h2>
        </div>
        <ShieldCheck aria-hidden="true" size={24} />
      </div>
      <div className="legal-check-list">
        <div>
          <CheckCircle2 aria-hidden="true" size={17} />
          <span>Сначала ручная проверка сигнала и scope программы.</span>
        </div>
        <div>
          <Cpu aria-hidden="true" size={17} />
          <span>Потом только local/fork/test воспроизведение без broadcast.</span>
        </div>
        <div>
          <FileText aria-hidden="true" size={17} />
          <span>После этого приватный отчёт в официальный канал проекта.</span>
        </div>
      </div>
    </section>
  );
}

function QuickLinksPanel() {
  return (
    <section className="cockpit-panel cockpit-helper-card">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Быстрые рабочие ссылки</p>
          <h2>Куда идти дальше</h2>
        </div>
        <ClipboardList aria-hidden="true" size={24} />
      </div>
      <div className="quick-link-grid">
        <Link href="/dashboard">Все аудиты</Link>
        <Link href="/tools">Инструменты</Link>
        <Link href="/integrations">API-статус</Link>
        <Link href="/tg">Mini App</Link>
        <Link href="/disclosure">Disclosure</Link>
        <Link href="/billing">Тарифы</Link>
      </div>
    </section>
  );
}

function buildSupportDraft(task: FindingTask, contact: string) {
  return `Тема: responsible disclosure candidate для ${chainLabels[task.audit.chain]} контракта ${task.audit.address ?? task.audit.audit_id}

Здравствуйте, ${contact}.

Мы пишем вам приватно в рамках responsible disclosure.
wr3 отметил кандидатную security-проблему:

- Сеть: ${chainLabels[task.audit.chain]}
- Контракт / цель: ${task.audit.address ?? task.audit.audit_id}
- Текущая severity кандидата: ${task.severity === "none" ? "неизвестно" : severityLabels[task.severity]}
- Статус проверки: ${statusLabels[task.status]}

Важное про безопасность:
- Mainnet-транзакции не отправлялись.
- Средства не перемещались.
- Это не публичное обвинение.
- Кандидат требует ручной проверки до любых публичных заявлений.

Текущая сводка доказательств:
${task.note || "TODO: добавить ручную проверку, local/fork/test воспроизведение и impact statement."}

Следующий шаг:
Пожалуйста, подтвердите правильный security contact / bounty scope для этой цели. После ручной проверки мы можем отправить короткий технический отчёт.

С уважением,
команда wr3 research`;
}
