"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
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
  XCircle
} from "lucide-react";
import type { AuditState, Chain, Severity } from "@wr3/shared";
import { ScoutClient } from "@/components/ScoutClient";
import {
  appendDisclosureContact,
  approveDisclosurePacket,
  apiAssetUrl,
  createAudit,
  createDisclosureCase,
  dismissDisclosurePacket,
  getToolsStatus,
  listAudits,
  listDisclosureCases,
  markDisclosureManuallySent,
  prepareDisclosurePacket,
  requestDisclosureNeedsReview,
  retryAudit,
  type DashboardAudit,
  type DisclosureCase,
  type DisclosurePacket,
  type ToolsStatusResponse
} from "@/lib/api";
import { auditStateLabels, chainLabels, severityLabels } from "@/lib/i18n";

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
  verdict: string;
  verdictLabel: string;
  readinessLabel: string;
  explanation: string;
  evidenceGaps: string[];
  falsePositiveRisk: string;
  canCreateDisclosure: boolean;
  primaryFindingId: string | null;
  supportContact?: string;
  disclosureCaseId?: string;
};

type CockpitTab = "scan" | "team" | "scout" | "findings" | "disclosure" | "engine" | "links";

const cockpitTabs: { id: CockpitTab; label: string; description: string; icon: LucideIcon }[] = [
  { id: "scan", label: "Скан", description: "адрес или код", icon: Radar },
  { id: "team", label: "Команда", description: "рабочая сводка", icon: Gauge },
  { id: "scout", label: "24/7 Scout", description: "цели из сетей", icon: Activity },
  { id: "findings", label: "Очередь багов", description: "проверка кандидатов", icon: Bug },
  { id: "disclosure", label: "Обращение", description: "канал и отчёт", icon: Send },
  { id: "engine", label: "Движок", description: "инструменты и здоровье", icon: Cpu },
  { id: "links", label: "Навигация", description: "разделы платформы", icon: ClipboardList }
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
  if (audit.primary_verdict === "can_write") return "report_draft";
  if (audit.primary_verdict === "do_not_write") return "dismissed";
  if (audit.state === "failed") return "blocked";
  if (audit.highest_severity === "critical" || audit.highest_severity === "high") return "needs_validation";
  if (audit.finding_count > 0) return "candidate";
  if (audit.state === "needs_source") return "blocked";
  return "candidate";
}

function taskTitle(audit: DashboardAudit) {
  const severity = audit.highest_severity ? severityLabels[audit.highest_severity] : "кандидат";
  const address = audit.address ? shortAddress(audit.address) : shortAddress(audit.audit_id);
  return audit.primary_finding_title || `${severity} · ${chainLabels[audit.chain]} · ${address}`;
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

function formatDisclosureDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit"
  }).format(new Date(value));
}

function apiAssetHref(path?: string | null) {
  return apiAssetUrl(path);
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
        nextStep: audit.primary_next_step || statusNext[status],
        verdict: audit.primary_verdict,
        verdictLabel: audit.primary_verdict_label,
        readinessLabel: audit.primary_readiness_label,
        explanation: audit.primary_explanation,
        evidenceGaps: audit.primary_evidence_gaps,
        falsePositiveRisk: audit.primary_false_positive_risk,
        canCreateDisclosure: audit.can_create_disclosure,
        primaryFindingId: audit.primary_finding_id,
        supportContact: override.supportContact,
        disclosureCaseId: override.disclosureCaseId,
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
    team: "live",
    scout: "авто",
    findings: metrics.openTasks,
    disclosure: metrics.legalBlockers,
    engine: `${engineHealth}%`,
    links: "меню"
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
          <div className="cockpit-tab-grid cockpit-tab-grid-links">
            <div className="cockpit-tab-column">
              <QuickScanPanel />
            </div>
          </div>
        ) : null}

        {activeTab === "team" ? (
          <div className="cockpit-tab-grid cockpit-tab-grid-links">
            <MetricsPanel metrics={metrics} onOpenTab={setActiveTab} />
          </div>
        ) : null}

        {activeTab === "scout" ? (
          <ScoutClient />
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
            </div>
          </div>
        ) : null}

        {activeTab === "disclosure" ? (
          <div className="cockpit-tab-grid cockpit-tab-grid-links">
            <div className="cockpit-tab-column">
              <DisclosureWorkspacePanel
                disclosures={disclosures}
                onPatch={patchTask}
                onRefresh={load}
                task={selectedTask}
              />
            </div>
          </div>
        ) : null}

        {activeTab === "engine" ? (
          <div className="cockpit-tab-grid cockpit-tab-grid-links">
            <div className="cockpit-tab-column">
              <BountyRadar tasks={tasks} toolsStatus={toolsStatus} />
            </div>
          </div>
        ) : null}

        {activeTab === "links" ? (
          <div className="cockpit-tab-grid cockpit-tab-grid-links">
            <QuickLinksPanel />
          </div>
        ) : null}
      </section>
    </section>
  );
}

type MetricId =
  | "highCriticalWaiting"
  | "reportsReady"
  | "disclosureDeadlines"
  | "engineHealth"
  | "failedScans"
  | "openTasks"
  | "legalBlockers";

type TeamMetric = {
  id: MetricId;
  icon: LucideIcon;
  label: string;
  value: string | number;
  tone: "red" | "yellow" | "green" | "blue";
  signal: string;
  hint: string;
  brief: string;
  summary: string;
  state: string;
  nextStep: string;
  targetTab: CockpitTab;
  targetLabel: string;
};

function TeamSignalRow({
  metric,
  selected,
  onSelect
}: {
  metric: TeamMetric;
  selected: boolean;
  onSelect: () => void;
}) {
  const Icon = metric.icon;
  return (
    <button
      aria-pressed={selected}
      className={`team-signal-row team-signal-row-${metric.tone} ${selected ? "team-signal-row-active" : ""}`}
      onClick={onSelect}
      type="button"
    >
      <span className="team-signal-icon"><Icon aria-hidden="true" size={18} /></span>
      <span className="team-signal-copy">
        <b>{metric.label}</b>
        <small>{metric.hint}</small>
      </span>
      <strong>{metric.value}</strong>
      <em>{metric.signal}</em>
    </button>
  );
}

function MetricsPanel({
  metrics,
  onOpenTab
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
  onOpenTab: (tab: CockpitTab) => void;
}) {
  const [selectedMetricId, setSelectedMetricId] = useState<MetricId>("highCriticalWaiting");
  const metricItems: TeamMetric[] = [
    {
      id: "highCriticalWaiting",
      icon: ShieldAlert,
      label: "High/Critical на проверке",
      value: metrics.highCriticalWaiting,
      tone: "red",
      signal: "приоритет",
      hint: "сначала команда",
      brief: "Срочные сигналы без смешивания с общей очередью",
      summary: "Сколько серьёзных кандидатов сейчас ждут ручной проверки команды.",
      state: metrics.highCriticalWaiting
        ? "Есть срочные находки: их нельзя смешивать с обычной очередью."
        : "Срочных High/Critical кандидатов сейчас нет.",
      nextStep: "Открыть очередь, выбрать верхний сигнал, назначить ответственного и закрыть ручную проверку.",
      targetTab: "findings",
      targetLabel: "Открыть очередь багов"
    },
    {
      id: "reportsReady",
      icon: FileText,
      label: "Отчёты готовы",
      value: metrics.reportsReady,
      tone: "blue",
      signal: "черновик",
      hint: "проверить текст",
      brief: "Черновики, которые уже можно готовить к приватной отправке",
      summary: "Сколько задач уже дошли до черновика приватного отчёта.",
      state: metrics.reportsReady
        ? "Есть готовые черновики: их нужно проверить перед отправкой."
        : "Готовых черновиков отчёта пока нет.",
      nextStep: "Перейти в обращение и сверить официальный канал проекта перед отправкой.",
      targetTab: "disclosure",
      targetLabel: "Открыть обращение"
    },
    {
      id: "disclosureDeadlines",
      icon: BellRing,
      label: "Сроки disclosure",
      value: metrics.disclosureDeadlines,
      tone: "yellow",
      signal: "контакт",
      hint: "не потерять ответ",
      brief: "Активные контакты и дедлайны, которые держит команда",
      summary: "Активные disclosure-кейсы и контакты, которые команда должна держать под контролем.",
      state: metrics.disclosureDeadlines
        ? "Есть активные обращения: важно не потерять фоллоу-апы и ответы."
        : "Активных disclosure-кейсов сейчас нет.",
      nextStep: "Проверить текущую цель, официальный security contact и историю контакта.",
      targetTab: "disclosure",
      targetLabel: "Открыть обращение"
    },
    {
      id: "engineHealth",
      icon: Gauge,
      label: "Здоровье движка",
      value: `${metrics.engineHealth}%`,
      tone: "green",
      signal: "движок",
      hint: "готовность движка",
      brief: "Локальный движок и анализаторы готовы к рабочим прогонам",
      summary: "Готовность локального набора анализаторов и обязательных инструментов.",
      state:
        metrics.engineHealth === 100
          ? "Локальный движок готов к рабочим прогонам."
          : "Часть обязательных инструментов требует внимания.",
      nextStep: "Открыть радар сетей и проверить, где ограничения мешают движению дальше.",
      targetTab: "engine",
      targetLabel: "Открыть движок"
    },
    {
      id: "failedScans",
      icon: XCircle,
      label: "Упавшие сканы",
      value: metrics.failedScans,
      tone: "red",
      signal: "повтор",
      hint: "разобрать сбой",
      brief: "Сбои прогонов, которые надо поднять до результата",
      summary: "Сканы, которые не дошли до результата и требуют повторного запуска или разбора ошибки.",
      state: metrics.failedScans ? "Есть технические сбои в прогонах." : "Упавших сканов сейчас нет.",
      nextStep: "Открыть очередь, найти failed-задачи и перезапустить безопасный прогон.",
      targetTab: "findings",
      targetLabel: "Открыть очередь багов"
    },
    {
      id: "openTasks",
      icon: ClipboardList,
      label: "Открытые задачи",
      value: metrics.openTasks,
      tone: "blue",
      signal: "очередь",
      hint: "распределить работу",
      brief: "Живая очередь команды: что ещё не закрыто и не отправлено",
      summary: "Все задачи команды, которые ещё не отклонены и не закрыты как отправленные.",
      state: metrics.openTasks ? "Очередь активна: нужно выбирать приоритеты." : "Открытых задач сейчас нет.",
      nextStep: "Открыть очередь, отфильтровать по статусу и назначить владельца следующей задачи.",
      targetTab: "findings",
      targetLabel: "Открыть очередь багов"
    },
    {
      id: "legalBlockers",
      icon: BookOpenCheck,
      label: "Юр. блокеры",
      value: metrics.legalBlockers,
      tone: "yellow",
      signal: "проверка",
      hint: "scope и текст",
      brief: "Задачи, которые нельзя выпускать без аккуратной проверки",
      summary: "Задачи, где нужна аккуратность по формулировкам, scope или приватному каналу.",
      state: metrics.legalBlockers
        ? "Есть задачи с юридическим review: их нельзя отправлять как обычный репорт."
        : "Юридических блокеров сейчас нет.",
      nextStep: "Перейти в обращение и сверить канал, формулировки и ограничения по текущей цели.",
      targetTab: "disclosure",
      targetLabel: "Открыть обращение"
    }
  ];
  const selectedMetric = metricItems.find((metric) => metric.id === selectedMetricId) ?? metricItems[0];

  return (
    <section className={`team-command-panel team-command-panel-${selectedMetric.tone}`} aria-label="Командная сводка">
      <aside className="team-command-rail">
        <div className="team-rail-head">
          <p className="eyebrow">Команда</p>
          <h2>Пульт смены</h2>
          <span>{metricItems.length} сигналов</span>
        </div>
        <div className="team-signal-list">
          {metricItems.map((metric) => (
            <TeamSignalRow
              key={metric.id}
              metric={metric}
              onSelect={() => setSelectedMetricId(metric.id)}
              selected={selectedMetric.id === metric.id}
            />
          ))}
        </div>
      </aside>
      <article className="team-briefing-deck" aria-live="polite">
        <div className="team-briefing-head">
          <div>
            <p className="eyebrow">Оперативный брифинг</p>
            <h2>{selectedMetric.brief}</h2>
          </div>
          <div className="team-briefing-number">
            <span>{selectedMetric.signal}</span>
            <strong>{selectedMetric.value}</strong>
          </div>
        </div>
        <div className="team-briefing-body">
          <section className="team-briefing-focus">
            <span>{selectedMetric.label}</span>
            <p>{selectedMetric.summary}</p>
          </section>
          <div className="team-briefing-grid">
            <div>
              <span>Состояние</span>
              <b>{selectedMetric.state}</b>
            </div>
            <div>
              <span>Следующий шаг</span>
              <b>{selectedMetric.nextStep}</b>
            </div>
            <div>
              <span>Рабочая зона</span>
              <b>{selectedMetric.targetLabel}</b>
            </div>
          </div>
        </div>
        <footer className="team-briefing-action">
          <span>Откроет нужную вкладку и сохранит текущий контекст команды.</span>
          <button type="button" onClick={() => onOpenTab(selectedMetric.targetTab)}>
            {selectedMetric.targetLabel}
          </button>
        </footer>
      </article>
    </section>
  );
}

function DisclosureWorkspacePanel({
  task,
  disclosures,
  onPatch,
  onRefresh
}: {
  task: FindingTask | null;
  disclosures: DisclosureCase[];
  onPatch: (taskId: string, patch: TaskOverride) => void;
  onRefresh: () => Promise<void>;
}) {
  const [supportContact, setSupportContact] = useState("security@example.org");
  const [contactSource, setContactSource] = useState("security_txt");
  const [manualChannel, setManualChannel] = useState<"manual_email" | "bug_bounty_portal">("manual_email");
  const [packet, setPacket] = useState<DisclosurePacket | null>(null);
  const [checks, setChecks] = useState({
    scopeVerified: false,
    contactVerified: false,
    noPublicPoc: true,
    humanReviewDone: false
  });
  const [localCaseId, setLocalCaseId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [isLogging, setIsLogging] = useState(false);

  const activeCase = useMemo(() => {
    if (!task) return null;
    return (
      disclosures.find((item) => item.id === task.disclosureCaseId) ??
      disclosures.find((item) => item.id === localCaseId) ??
      disclosures.find((item) => task.primaryFindingId && item.finding_id === task.primaryFindingId) ??
      null
    );
  }, [disclosures, localCaseId, task]);

  useEffect(() => {
    setSupportContact(task?.supportContact ?? activeCase?.project_contact ?? "security@example.org");
    setContactSource(activeCase?.contact_source ?? "security_txt");
    setLocalCaseId(task?.disclosureCaseId ?? null);
    setPacket(null);
    setChecks({
      scopeVerified: false,
      contactVerified: false,
      noPublicPoc: true,
      humanReviewDone: false
    });
    setStatus(null);
    setError(null);
  }, [task?.id, task?.supportContact, task?.disclosureCaseId, activeCase?.project_contact, activeCase?.contact_source]);

  if (!task) {
    return (
      <section className="cockpit-panel disclosure-workspace-panel">
        <div className="cockpit-panel-head">
          <div>
            <p className="eyebrow">Обращение</p>
            <h2>Выбери задачу из очереди</h2>
          </div>
          <Send aria-hidden="true" size={24} />
        </div>
        <p className="muted-copy">Здесь появится черновик responsible disclosure, checklist и лог ручной отправки.</p>
      </section>
    );
  }

  const activeTask = task;
  const hasFindingForPacket = Boolean(activeTask.primaryFindingId);
  const checklistComplete = checks.scopeVerified && checks.contactVerified && checks.noPublicPoc && checks.humanReviewDone;
  const caseId = activeCase?.id ?? localCaseId ?? activeTask.disclosureCaseId ?? null;
  const supportDraft = packet?.draft_message ?? activeCase?.draft_message ?? buildSupportDraft(activeTask, supportContact || "official security contact");
  const target = activeTask.audit.address ?? activeTask.audit.audit_id;
  const packetState = packet?.readiness_state ?? activeCase?.readiness_state ?? activeCase?.status ?? "not_prepared";
  const canApprove = Boolean((packet?.needs_human_approval ?? activeCase?.needs_human_approval) && checklistComplete);
  const canLogSent = Boolean(packet?.approved_to_contact ?? activeCase?.approved_to_contact);

  async function createDraftCase() {
    setError(null);
    setStatus(null);
    if (!activeTask.primaryFindingId) {
      setError("Рано готовить packet: у задачи нет finding.");
      return;
    }
    if (!supportContact.trim()) {
      setError("Сначала укажи официальный security/support contact.");
      return;
    }
    if (!checklistComplete) {
      setError("Закрой checklist перед созданием черновика: scope, контакт, приватность и human review.");
      return;
    }
    setIsCreating(true);
    try {
      const created = await prepareDisclosurePacket({
        audit_id: activeTask.audit.audit_id,
        finding_id: activeTask.primaryFindingId,
        official_contact: supportContact.trim(),
        contact_source: contactSource,
        project_name: activeTask.audit.project_key,
        scope_note: `Scope verified manually. ${activeTask.nextStep} Passive/local/fork only, no mainnet broadcast.`
      });
      setPacket(created);
      setLocalCaseId(created.case_id);
      onPatch(activeTask.id, { status: "report_draft", supportContact: supportContact.trim(), disclosureCaseId: created.case_id });
      setStatus(
        created.needs_human_approval
          ? `Packet почти готов: PDFs/draft есть, нужен approve. Case ${created.case_id}`
          : `Packet создан как ${created.readiness_state}. Telegram normal mode пока не будет шуметь.`
      );
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Черновик обращения не создался");
    } finally {
      setIsCreating(false);
    }
  }

  async function approvePacket() {
    setError(null);
    setStatus(null);
    if (!caseId) {
      setError("Сначала подготовь disclosure packet.");
      return;
    }
    setIsApproving(true);
    try {
      const next = await approveDisclosurePacket(caseId, { note: "Approved from wr3 command center." });
      setPacket(next);
      onPatch(activeTask.id, { status: "report_draft", supportContact: supportContact.trim(), disclosureCaseId: caseId });
      setStatus("Approve принят: теперь Telegram может показать “можно писать” с safe draft и external PDF.");
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve не прошёл");
    } finally {
      setIsApproving(false);
    }
  }

  async function sendNeedsReview() {
    setError(null);
    setStatus(null);
    if (!caseId) return;
    setIsReviewing(true);
    try {
      const next = await requestDisclosureNeedsReview(caseId, { note: "Team requested more review from command center." });
      setPacket(next);
      setStatus("Case возвращён в review. В normal Telegram он не будет пушиться.");
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось вернуть в review");
    } finally {
      setIsReviewing(false);
    }
  }

  async function dismissPacket() {
    setError(null);
    setStatus(null);
    if (!caseId) return;
    setIsReviewing(true);
    try {
      const next = await dismissDisclosurePacket(caseId, { note: "Dismissed from command center." });
      setPacket(next);
      onPatch(activeTask.id, { status: "dismissed", disclosureCaseId: caseId });
      setStatus("Case отклонён и не будет попадать в Telegram normal mode.");
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отклонить case");
    } finally {
      setIsReviewing(false);
    }
  }

  async function logManualSend() {
    setError(null);
    setStatus(null);
    if (!caseId) {
      setError("Сначала создай disclosure case, потом логируй ручную отправку.");
      return;
    }
    if (!supportContact.trim()) {
      setError("Укажи, куда вручную отправили сообщение.");
      return;
    }
    setIsLogging(true);
    try {
      const next = await markDisclosureManuallySent(caseId, {
        channel: manualChannel,
        note: `Contact: ${supportContact.trim()}. No automatic delivery was performed by wr3.`
      });
      setPacket(next);
      onPatch(activeTask.id, { status: "submitted", supportContact: supportContact.trim(), disclosureCaseId: caseId });
      setStatus(`Ручная отправка залогирована в case ${caseId}. Наружу wr3 ничего не отправлял.`);
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ручную отправку не удалось залогировать");
    } finally {
      setIsLogging(false);
    }
  }

  return (
    <section className="cockpit-panel disclosure-workspace-panel">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Обращение</p>
          <h2>Черновик, проверка канала и ручной лог</h2>
        </div>
        <Send aria-hidden="true" size={24} />
      </div>

      <div className="disclosure-workspace-grid">
        <div className="disclosure-compose-column">
          <article className="disclosure-selected-task">
            <span>Выбранная задача</span>
            <strong>{task.title}</strong>
            <p>{chainLabels[task.audit.chain]} · {shortAddress(target)} · {task.verdictLabel} · {task.readinessLabel}</p>
            <small>{task.canCreateDisclosure ? "Можно готовить приватное обращение после checklist." : "Пока только ручная проверка: не хватает сигнала для обращения."}</small>
          </article>

          <label className="disclosure-contact-control">
            Официальный security/support contact
            <input
              value={supportContact}
              onChange={(event) => setSupportContact(event.target.value)}
              placeholder="security@example.org или ссылка на bounty portal"
            />
          </label>

          <label className="disclosure-contact-control">
            Источник контакта
            <select value={contactSource} onChange={(event) => setContactSource(event.target.value)}>
              <option value="bug_bounty_portal">bug_bounty_portal</option>
              <option value="security_txt">security_txt</option>
              <option value="github_security_policy">github_security_policy</option>
              <option value="security_md">security_md</option>
              <option value="official_website_email">official_website_email</option>
              <option value="official_website_contact_form">official_website_contact_form</option>
              <option value="x_twitter">x_twitter только review</option>
              <option value="telegram">telegram только review</option>
              <option value="discord">discord только review</option>
            </select>
          </label>

          <div className="disclosure-checklist" aria-label="Responsible disclosure checklist">
            <label>
              <input
                checked={checks.scopeVerified}
                onChange={(event) => setChecks((current) => ({ ...current, scopeVerified: event.target.checked }))}
                type="checkbox"
              />
              Scope программы проверен
            </label>
            <label>
              <input
                checked={checks.contactVerified}
                onChange={(event) => setChecks((current) => ({ ...current, contactVerified: event.target.checked }))}
                type="checkbox"
              />
              Официальный контакт подтверждён
            </label>
            <label>
              <input
                checked={checks.noPublicPoc}
                onChange={(event) => setChecks((current) => ({ ...current, noPublicPoc: event.target.checked }))}
                type="checkbox"
              />
              Нет публичного PoC и mainnet exploit steps
            </label>
            <label>
              <input
                checked={checks.humanReviewDone}
                onChange={(event) => setChecks((current) => ({ ...current, humanReviewDone: event.target.checked }))}
                type="checkbox"
              />
              Human review сделан командой
            </label>
          </div>

          <article className="safe-draft-preview">
            <span>Safe draft preview</span>
            <pre>{supportDraft}</pre>
          </article>
        </div>

        <aside className="disclosure-ops-column">
          <article className="disclosure-case-status">
            <span>Активный case</span>
            <strong>{caseId ?? "ещё не создан"}</strong>
            <p>
              {activeCase
                ? `Readiness: ${packetState}. Дедлайн: ${formatDisclosureDate(activeCase.deadline_next)}.`
                : "Подготовь packet, чтобы появились PDFs, safe draft и Telegram review context."}
            </p>
            <div className="disclosure-case-links">
              {(packet?.internal_pdf_url ?? activeCase?.internal_pdf_url) ? <a href={apiAssetHref(packet?.internal_pdf_url ?? activeCase?.internal_pdf_url)} target="_blank" rel="noreferrer">Internal PDF</a> : null}
              {(packet?.external_pdf_url ?? activeCase?.external_pdf_url) ? <a href={apiAssetHref(packet?.external_pdf_url ?? activeCase?.external_pdf_url)} target="_blank" rel="noreferrer">External PDF</a> : null}
            </div>
          </article>

          <div className="disclosure-action-stack">
            <button type="button" onClick={createDraftCase} disabled={isCreating || !hasFindingForPacket || !checklistComplete}>
              {isCreating ? <Loader2 className="spin" aria-hidden="true" size={16} /> : <Send aria-hidden="true" size={16} />}
              Подготовить packet + PDFs
            </button>
            <button type="button" className="secondary-button" onClick={approvePacket} disabled={isApproving || !canApprove}>
              {isApproving ? <Loader2 className="spin" aria-hidden="true" size={16} /> : <CheckCircle2 aria-hidden="true" size={16} />}
              Approve: можно писать
            </button>
            <div className="disclosure-review-row">
              <button type="button" className="secondary-button" onClick={sendNeedsReview} disabled={isReviewing || !caseId}>
                Needs Review
              </button>
              <button type="button" className="secondary-button danger-button" onClick={dismissPacket} disabled={isReviewing || !caseId}>
                Dismiss
              </button>
            </div>
            <label>
              Канал ручной отправки
              <select value={manualChannel} onChange={(event) => setManualChannel(event.target.value as "manual_email" | "bug_bounty_portal")}>
                <option value="manual_email">manual_email</option>
                <option value="bug_bounty_portal">bug_bounty_portal</option>
              </select>
            </label>
            <button type="button" className="secondary-button" onClick={logManualSend} disabled={isLogging || !caseId || !canLogSent}>
              {isLogging ? <Loader2 className="spin" aria-hidden="true" size={16} /> : <CheckCircle2 aria-hidden="true" size={16} />}
              Я вручную отправил сообщение
            </button>
          </div>

          {status ? <p className="empty-state">{status}</p> : null}
          {error ? <p className="error-box">{error}</p> : null}

          <div className="disclosure-case-list">
            <div className="scout-section-head">
              <strong>Активные disclosure cases</strong>
              <span>{disclosures.length}</span>
            </div>
            {disclosures.length === 0 ? (
              <p className="empty-state">Кейсов пока нет. Они появятся после создания черновика.</p>
            ) : (
              disclosures.slice(0, 8).map((item) => (
                <article className={item.id === caseId ? "disclosure-case-row disclosure-case-row-active" : "disclosure-case-row"} key={item.id}>
                  <strong>{shortAddress(item.id)}</strong>
                  <span>{item.readiness_state || item.status}</span>
                  <small>deadline {formatDisclosureDate(item.deadline_next)}</small>
                </article>
              ))
            )}
          </div>
        </aside>
      </div>
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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        user_intent: "pre_launch_self_check"
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
  const [isRetrying, setIsRetrying] = useState(false);

  useEffect(() => {
    setDraftNote(task?.note ?? "");
    setSupportContact(task?.supportContact ?? "security@example.org");
    setCaseStatus(null);
    setCaseError(null);
  }, [task?.id, task?.note, task?.supportContact]);

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
    if (!activeTask.canCreateDisclosure || !activeTask.primaryFindingId) {
      setCaseError("Рано создавать disclosure: не хватает подтверждения, точной location или сильного static+AI/PoC сигнала.");
      return;
    }
    setIsCreatingCase(true);
    try {
      const created = await createDisclosureCase({
        finding_id: activeTask.primaryFindingId,
        project_contact: supportContact,
        scope_note: `Внутренняя кандидатная задача wr3. Вердикт: ${activeTask.verdictLabel}. ${activeTask.nextStep} Без активных mainnet-действий.`
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

  async function retrySelectedAudit() {
    setCaseError(null);
    setIsRetrying(true);
    try {
      if (activeTask.audit.state === "completed") {
        if (!activeTask.audit.address) {
          throw new Error("Для повторного прогона source-only аудита нужно запустить новый скан через вкладку “Скан”.");
        }
        const created = await createAudit({
          chain: activeTask.audit.chain,
          address: activeTask.audit.address,
          source: "",
          allow_bytecode_only: true,
          requested_depth: activeTask.audit.requested_depth,
          visibility: "private",
          user_intent: "pre_launch_self_check"
        });
        onPatch(activeTask.id, { status: "needs_validation", note: `${draftNote}\nСоздан новый прогон: ${created.audit_id}.`.trim() });
        setCaseStatus("Создан новый прогон скана. Открываю новый отчёт.");
        window.location.href = `/audits/${created.audit_id}?owner_token=${encodeURIComponent(created.owner_access_token)}`;
        return;
      }
      await retryAudit(activeTask.audit.audit_id, activeTask.audit.owner_access_token ?? undefined);
      onPatch(activeTask.id, { status: "needs_validation", note: `${draftNote}\nПовторная проверка запрошена.`.trim() });
      setCaseStatus("Повторная проверка запрошена. Обнови очередь через несколько секунд.");
    } catch (err) {
      setCaseError(err instanceof Error ? err.message : "Повторная проверка не запустилась");
    } finally {
      setIsRetrying(false);
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
          <dt>Вердикт</dt>
          <dd>{task.verdictLabel}</dd>
        </div>
        <div>
          <dt>Готовность</dt>
          <dd>{task.readinessLabel}</dd>
        </div>
        <div>
          <dt>Аудит</dt>
          <dd><Link href={href}>{shortAddress(task.audit.audit_id)}</Link></dd>
        </div>
        <div>
          <dt>Состояние</dt>
          <dd>{auditStateLabels[task.audit.state as AuditState]}</dd>
        </div>
        <div>
          <dt>Находки</dt>
          <dd>{task.audit.finding_count}</dd>
        </div>
        <div>
          <dt>FP risk</dt>
          <dd>{task.falsePositiveRisk}</dd>
        </div>
      </dl>

      <article className={`finding-verdict finding-verdict-${task.verdict}`}>
        {task.canCreateDisclosure ? <CheckCircle2 aria-hidden="true" size={18} /> : <ShieldAlert aria-hidden="true" size={18} />}
        <div>
          <strong>{task.verdictLabel}</strong>
          <span>{task.explanation}</span>
        </div>
      </article>

      {task.evidenceGaps.length ? (
        <article className="evidence-gap-box">
          <strong>Чего не хватает перед письмом</strong>
          <ul>
            {task.evidenceGaps.map((gap) => <li key={gap}>{gap}</li>)}
          </ul>
        </article>
      ) : null}

      <div className="task-action-grid">
        <Link className="button-like" href={href}>
          <FileText aria-hidden="true" size={16} />
          Полный audit
        </Link>
        <button type="button" className="secondary-button danger-button" onClick={() => onPatch(task.id, { status: "dismissed" })}>
          <XCircle aria-hidden="true" size={16} />
          Отклонить FP
        </button>
        <button type="button" className="secondary-button" onClick={retrySelectedAudit} disabled={isRetrying}>
          {isRetrying ? <Loader2 className="spin" aria-hidden="true" size={16} /> : <RefreshCw aria-hidden="true" size={16} />}
          Повторить скан
        </button>
        <button type="button" className="secondary-button" onClick={createSupportCase} disabled={isCreatingCase || !task.canCreateDisclosure}>
          {isCreatingCase ? <Loader2 className="spin" aria-hidden="true" size={16} /> : <Send aria-hidden="true" size={16} />}
          Создать черновик обращения
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
Вердикт: ${task.verdictLabel}
Готовность: ${task.readinessLabel}
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

type RadarTone = "green" | "yellow" | "red";

type NetworkRadarSignal = {
  chain: Chain;
  label: string;
  tone: RadarTone;
  mode: string;
  configuredTargets: number;
  activeTargets: number;
  explorerSourcePull: string;
  lightChecks: string;
  deepAnalyzers: string;
  limitations: string;
  nextAction: string;
  x: string;
  y: string;
};

const radarToneLabels: Record<RadarTone, string> = {
  green: "Пропускаем / OK",
  yellow: "Ручная проверка",
  red: "Писать в поддержку о баге"
};

const radarChains: Array<{ chain: Chain; label: string; x: string; y: string }> = [
  { chain: "ethereum", label: "Ethereum", x: "21%", y: "32%" },
  { chain: "base", label: "Base", x: "49%", y: "22%" },
  { chain: "bsc", label: "BSC", x: "75%", y: "40%" },
  { chain: "arbitrum", label: "Arbitrum", x: "35%", y: "69%" },
  { chain: "solana", label: "Solana beta", x: "67%", y: "75%" }
];

function uniqueTargetCount(tasks: FindingTask[]) {
  return new Set(tasks.map((task) => task.audit.address ?? task.audit.audit_id)).size;
}

function supportReady(task: FindingTask) {
  return task.audit.primary_verdict === "can_write" || ["validated", "report_draft"].includes(task.status);
}

function manualReviewNeeded(task: FindingTask) {
  return ["candidate", "needs_validation", "reproducing", "blocked"].includes(task.status) || task.audit.limitations_count > 0;
}

function buildNetworkSignal(
  chain: { chain: Chain; label: string; x: string; y: string },
  tasks: FindingTask[],
  toolsStatus: ToolsStatusResponse | null
): NetworkRadarSignal {
  const chainTasks = tasks.filter((task) => task.audit.chain === chain.chain);
  const configuredTargets = uniqueTargetCount(chainTasks);
  const activeTargets = uniqueTargetCount(
    chainTasks.filter((task) => !["dismissed", "submitted"].includes(task.status) && task.audit.state !== "failed")
  );
  const readyTasks = chainTasks.filter(supportReady);
  const reviewTasks = chainTasks.filter(manualReviewNeeded);
  const findingCount = chainTasks.reduce((sum, task) => sum + task.audit.finding_count, 0);
  const completed = chainTasks.filter((task) => task.audit.state === "completed").length;
  const failed = chainTasks.filter((task) => task.audit.state === "failed").length;
  const limitationsCount = chainTasks.reduce((sum, task) => sum + task.audit.limitations_count, 0);
  const tone: RadarTone = readyTasks.length ? "red" : reviewTasks.length || !activeTargets ? "yellow" : "green";
  const mode =
    tone === "red"
      ? "support_workflow_ready"
      : tone === "yellow"
        ? activeTargets
          ? "manual_review"
          : "needs_allowed_targets"
        : "ok_watch";
  const explorerSourcePull =
    chain.chain === "solana"
      ? "beta / ручная проверка источников"
      : activeTargets
        ? "история аудитов + локальные explorer/API данные"
        : "нет активных целей";
  const toolReadiness = toolsStatus
    ? `${toolsStatus.required_installed}/${toolsStatus.required_total} обязательных tools`
    : "статус tools недоступен";
  const limitations = [
    configuredTargets ? null : "нет разрешённых целей в текущей очереди",
    limitationsCount ? `${limitationsCount} ограничений из аудитов` : null,
    failed ? `${failed} неуспешных прогонов` : null,
    chain.chain === "solana" ? "Solana пока beta-режим" : null
  ].filter(Boolean).join("; ");

  return {
    ...chain,
    tone,
    mode,
    configuredTargets,
    activeTargets,
    explorerSourcePull,
    lightChecks: chainTasks.length
      ? `${completed}/${chainTasks.length} завершено, ${findingCount} находок`
      : "нет прогонов по сети",
    deepAnalyzers: toolReadiness,
    limitations: limitations || "нет явных ограничений по текущей очереди",
    nextAction:
      tone === "red"
        ? "Открыть обращение, собрать responsible disclosure и приватный отчёт. Авто-отправки нет."
        : tone === "yellow"
          ? "Проверить scope, ограничения и воспроизводимость в local/fork/test перед движением дальше."
          : "Срочного действия нет: можно переходить к следующей сети или добавлять новые разрешённые цели."
  };
}

function BountyRadar({ tasks, toolsStatus }: { tasks: FindingTask[]; toolsStatus: ToolsStatusResponse | null }) {
  const [selectedChain, setSelectedChain] = useState<Chain>("ethereum");
  const [drift, setDrift] = useState({ x: 0, y: 0 });
  const signals = useMemo(
    () => radarChains.map((chain) => buildNetworkSignal(chain, tasks, toolsStatus)),
    [tasks, toolsStatus]
  );
  const selectedSignal = signals.find((signal) => signal.chain === selectedChain) ?? signals[0];
  const urgentCount = signals.filter((signal) => signal.tone === "red").length;

  return (
    <section className="cockpit-panel bounty-radar network-radar-card">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Звёздный радар сетей</p>
          <h2>Где нужен следующий шаг</h2>
        </div>
        <Bug aria-hidden="true" size={24} />
      </div>
      <div className="network-radar-legend" aria-label="Легенда статусов радара">
        <span className="network-radar-green">Пропускаем / OK</span>
        <span className="network-radar-yellow">Ручная проверка</span>
        <span className="network-radar-red">Писать в поддержку о баге</span>
      </div>
      <div className="network-radar-layout">
        <div
          className="network-radar-map"
          aria-label="Карта blockchain-сетей"
          onPointerLeave={() => setDrift({ x: 0, y: 0 })}
          onPointerMove={(event) => {
            const bounds = event.currentTarget.getBoundingClientRect();
            setDrift({
              x: ((event.clientX - bounds.left) / bounds.width - 0.5) * 12,
              y: ((event.clientY - bounds.top) / bounds.height - 0.5) * 12
            });
          }}
          style={{
            "--radar-drift-x": `${drift.x}px`,
            "--radar-drift-y": `${drift.y}px`
          } as CSSProperties}
        >
          <div className="network-radar-grid" aria-hidden="true" />
          <div className="network-radar-orbit network-radar-orbit-one" aria-hidden="true" />
          <div className="network-radar-orbit network-radar-orbit-two" aria-hidden="true" />
          <div className="network-radar-core" aria-hidden="true">
            <strong>{urgentCount}</strong>
            <span>support-ready</span>
          </div>
          {signals.map((signal) => (
            <button
              aria-label={`${signal.label}: ${radarToneLabels[signal.tone]}`}
              aria-pressed={selectedSignal.chain === signal.chain}
              className={`network-radar-node network-radar-node-${signal.tone} ${
                selectedSignal.chain === signal.chain ? "network-radar-node-selected" : ""
              }`}
              key={signal.chain}
              onClick={() => setSelectedChain(signal.chain)}
              style={{
                "--node-x": signal.x,
                "--node-y": signal.y
              } as CSSProperties}
              type="button"
            >
              <span className="network-radar-star" aria-hidden="true" />
              <span className="network-radar-label">{signal.label}</span>
            </button>
          ))}
        </div>
        <article className={`network-radar-detail network-radar-detail-${selectedSignal.tone}`} aria-live="polite">
          <div>
            <p className="eyebrow">Выбранная сеть</p>
            <h3>{selectedSignal.label}</h3>
            <span>{radarToneLabels[selectedSignal.tone]}</span>
          </div>
          <dl className="network-radar-detail-grid">
            <div>
              <dt>mode</dt>
              <dd>{selectedSignal.mode}</dd>
            </div>
            <div>
              <dt>configured_targets / active_targets</dt>
              <dd>{selectedSignal.configuredTargets} / {selectedSignal.activeTargets}</dd>
            </div>
            <div>
              <dt>explorer_source_pull</dt>
              <dd>{selectedSignal.explorerSourcePull}</dd>
            </div>
          </dl>
          <div className="network-radar-detail-stack">
            <div>
              <strong>light_checks</strong>
              <p>{selectedSignal.lightChecks}</p>
            </div>
            <div>
              <strong>deep_analyzers</strong>
              <p>{selectedSignal.deepAnalyzers}</p>
            </div>
            <div>
              <strong>limitations</strong>
              <p>{selectedSignal.limitations}</p>
            </div>
            <div>
              <strong>Рекомендуемое действие</strong>
              <p>{selectedSignal.nextAction}</p>
            </div>
          </div>
        </article>
      </div>
    </section>
  );
}

const navigationSections = [
  {
    href: "/dashboard",
    title: "Все аудиты",
    description: "Список всех сканов: статусы, находки, повторный прогон и быстрый переход в отчёт."
  },
  {
    href: "/scout",
    title: "24/7 Scout",
    description: "Поиск целей по сетям и постановка новых контрактов в очередь аудитов."
  },
  {
    href: "/tools",
    title: "Инструменты",
    description: "Состояние локального audit-движка, установленных анализаторов и обязательных tools."
  },
  {
    href: "/integrations",
    title: "API-статус",
    description: "Подключение внешних источников, RPC, explorer API и готовность ingestion-потока."
  },
  {
    href: "/tg",
    title: "Mini App",
    description: "Мобильный рабочий интерфейс для Telegram, быстрого скана и просмотра результата."
  },
  {
    href: "/disclosure",
    title: "Обращение",
    description: "Подготовка responsible disclosure, приватного отчёта и истории контакта с проектом."
  }
];

function QuickLinksPanel() {
  return (
    <section className="cockpit-panel cockpit-helper-card cockpit-navigation-panel">
      <div className="cockpit-panel-head">
        <div>
          <p className="eyebrow">Навигация</p>
          <h2>Разделы платформы</h2>
        </div>
        <ClipboardList aria-hidden="true" size={24} />
      </div>
      <div className="quick-link-grid">
        {navigationSections.map((section) => (
          <Link href={section.href} key={section.href}>
            <span>{section.title}</span>
            <p>{section.description}</p>
          </Link>
        ))}
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
- Вердикт wr3: ${task.verdictLabel}
- Готовность: ${task.readinessLabel}
- Статус проверки: ${statusLabels[task.status]}

Важное про безопасность:
- Mainnet-транзакции не отправлялись.
- Средства не перемещались.
- Проверка велась только passive/local/fork.
- Мы не включаем working PoC или mainnet exploit steps в первое сообщение.
- Это не публичное обвинение.
- Кандидат требует ручной проверки до любых публичных заявлений.

Текущая сводка доказательств:
${task.note || "TODO: добавить ручную проверку, local/fork/test воспроизведение и impact statement."}

Чего ещё не хватает:
${task.evidenceGaps.length ? task.evidenceGaps.map((gap) => `- ${gap}`).join("\n") : "- Базовый evidence checklist закрыт."}

Следующий шаг:
Пожалуйста, подтвердите правильный security contact / bounty scope для этой цели. После ручной проверки мы можем отправить короткий технический отчёт.

С уважением,
команда wr3 research`;
}
