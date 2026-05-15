import type { AuditState, AuditSummary, Chain, Finding, ScoreBreakdown, Severity, Tier } from "@wr3/shared";

const LOCAL_API_BASE = "http://127.0.0.1:8001";
const CLIENT_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? LOCAL_API_BASE;
const SERVER_API_BASE =
  process.env.WR3_SERVER_API_BASE_URL ??
  process.env.API_INTERNAL_BASE_URL ??
  "http://127.0.0.1:8001";

function apiBaseUrl() {
  if (typeof window === "undefined") {
    return SERVER_API_BASE;
  }
  const isLocalhost = ["127.0.0.1", "localhost"].includes(window.location.hostname);
  if (isLocalhost && CLIENT_API_BASE.includes("trycloudflare.com")) {
    return LOCAL_API_BASE;
  }
  if (!isLocalhost && (CLIENT_API_BASE.startsWith("http://127.0.0.1") || CLIENT_API_BASE.startsWith("http://localhost") || CLIENT_API_BASE.includes("trycloudflare.com"))) {
    return "/api/wr3";
  }
  return CLIENT_API_BASE;
}

export type CreateAuditInput = {
  chain: Chain;
  address: string;
  source: string;
  allow_bytecode_only?: boolean;
  requested_depth: "preliminary" | "standard" | "deep";
  visibility: "private" | "public";
  user_intent: "pre_launch_self_check" | "third_party_research" | "monitoring";
  tier?: Tier;
};

export type PublicProjectSummary = {
  chain: Chain;
  address: string;
  score: ScoreBreakdown | null;
  safe_harbor_status: boolean;
  public_findings: Finding[];
  limitations: string[];
};

export type ToolStatus = {
  id: string;
  label: string;
  binary: string;
  category: string;
  installed: boolean;
  required_for_local_100: boolean;
  path: string | null;
  version: string;
  status: string;
  install_hint: string;
  safe_scope: string;
};

export type ToolsStatusResponse = {
  required_installed: number;
  required_total: number;
  installed_total: number;
  missing_required: string[];
  optional_missing: string[];
  status: "ready" | "partial";
  tools: ToolStatus[];
};

export type IntegrationStatusItem = {
  id: string;
  label: string;
  priority: string;
  category: string;
  status: "configured" | "free_fallback" | "manual" | "disabled" | "blocked";
  free_mode: string;
  used_by: string[];
  env_vars: string[];
  next_step: string;
  notes: string[];
};

export type IntegrationStatusResponse = {
  status: string;
  counts: Record<string, number>;
  rpc: Array<{
    chain: Chain;
    configured: boolean;
    source: string;
    free_fallback: boolean;
    url_host: string | null;
  }>;
  integrations: IntegrationStatusItem[];
};

export type CreateAuditResponse = {
  audit_id: string;
  state: string;
  status_url: string;
  estimated_wait_seconds: number;
  limitations: string[];
  owner_access_token: string;
  public_report_token: string | null;
};

export type DashboardAudit = {
  audit_id: string;
  owner_access_token: string | null;
  chain: Chain;
  address: string | null;
  state: AuditState;
  tier: Tier;
  requested_depth: "preliminary" | "standard" | "deep";
  score: ScoreBreakdown | null;
  finding_count: number;
  highest_severity: Severity | null;
  limitations_count: number;
  project_key: string;
  created_at: string;
  updated_at: string;
};

export type BillingPlan = {
  tier: Tier;
  name: string;
  price_usd_month: number;
  scan_quota: string;
  retention_days: number;
  poc_access: boolean;
  notes: string[];
};

export type TelegramEmulatorResponse = {
  ok: boolean;
  reply: string;
  audit_id?: string;
  state?: string;
  status_url?: string;
  limitations?: string[];
  watchlist_entry?: unknown;
  project?: PublicProjectSummary;
};

export type DisclosureCase = {
  id: string;
  finding_id: string;
  status: string;
  contact_log: string[];
  deadline_next: string;
  created_at: string;
};

export type AuthSession = {
  user_id: string;
  provider: string;
  subject: string;
  bearer_token: string;
  expires_at: string;
  limitations: string[];
};

export type WatchlistEntry = {
  id: string;
  user_id: string;
  chain: Chain;
  address: string;
  label: string | null;
  alert_channels: string[];
  status: string;
  created_at: string;
  limitations: string[];
};

function accessHeaders(ownerToken?: string): Record<string, string> {
  return ownerToken ? { "x-wr3-owner-token": ownerToken } : {};
}

function bearerHeaders(bearerToken?: string): Record<string, string> {
  return bearerToken ? { authorization: `Bearer ${bearerToken}` } : {};
}

function withOwnerToken(path: string, ownerToken?: string): string {
  if (!ownerToken) {
    return path;
  }
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}owner_token=${encodeURIComponent(ownerToken)}`;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Запрос завершился ошибкой ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function createAudit(input: CreateAuditInput, bearerToken?: string): Promise<CreateAuditResponse> {
  return apiFetch("/v1/audits", {
    method: "POST",
    headers: bearerHeaders(bearerToken),
    body: JSON.stringify({
      ...input,
      address: input.address || null,
      source: input.source || null
    })
  });
}

export async function listAudits(filters: {
  chain?: Chain | "";
  state?: AuditState | "";
  severity?: Severity | "";
} = {}): Promise<DashboardAudit[]> {
  const params = new URLSearchParams();
  if (filters.chain) params.set("chain", filters.chain);
  if (filters.state) params.set("state", filters.state);
  if (filters.severity) params.set("severity", filters.severity);
  const query = params.toString();
  return apiFetch(`/v1/audits${query ? `?${query}` : ""}`, {
    headers: { "x-wr3-reviewer": "true" }
  });
}

export async function getAudit(id: string, ownerToken?: string): Promise<AuditSummary> {
  return apiFetch(withOwnerToken(`/v1/audits/${id}`, ownerToken), {
    headers: accessHeaders(ownerToken)
  });
}

export async function getFindings(id: string, ownerToken?: string): Promise<Finding[]> {
  return apiFetch(withOwnerToken(`/v1/audits/${id}/findings`, ownerToken), {
    headers: accessHeaders(ownerToken)
  });
}

export async function getReportMarkdown(id: string, ownerToken?: string): Promise<string> {
  const response = await fetch(`${apiBaseUrl()}${withOwnerToken(`/v1/audits/${id}/report`, ownerToken)}`, {
    cache: "no-store",
    headers: accessHeaders(ownerToken)
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.text();
}

export async function retryAudit(id: string, ownerToken?: string): Promise<AuditSummary> {
  return apiFetch(withOwnerToken(`/v1/audits/${id}/retry`, ownerToken), {
    method: "POST",
    headers: accessHeaders(ownerToken)
  });
}

export async function deleteAudit(id: string, ownerToken?: string): Promise<{ audit_id: string; deleted: boolean }> {
  return apiFetch(withOwnerToken(`/v1/audits/${id}`, ownerToken), {
    method: "DELETE",
    headers: accessHeaders(ownerToken)
  });
}

export async function requestEmailSession(email: string) {
  return apiFetch("/v1/auth/email/request-link", {
    method: "POST",
    body: JSON.stringify({ email })
  });
}

export async function verifyTelegramInitData(input: {
  init_data: string;
  explicit_account_consent: boolean;
}): Promise<AuthSession> {
  return apiFetch("/v1/auth/telegram/init-data", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function addWatchlistEntry(
  input: { chain: Chain; address: string; label?: string | null; alert_channels?: string[] },
  bearerToken?: string
): Promise<WatchlistEntry> {
  return apiFetch("/v1/watchlist", {
    method: "POST",
    headers: bearerHeaders(bearerToken),
    body: JSON.stringify({
      ...input,
      label: input.label || null,
      alert_channels: input.alert_channels ?? ["telegram"]
    })
  });
}

export async function getPublicProject(chain: Chain, address: string): Promise<PublicProjectSummary> {
  return apiFetch(`/v1/projects/${chain}/${address}`);
}

export async function getToolsStatus(): Promise<ToolsStatusResponse> {
  return apiFetch("/v1/tools/status");
}

export async function getIntegrationStatus(): Promise<IntegrationStatusResponse> {
  return apiFetch("/v1/integrations/status");
}

export async function telegramEmulatorCommand(command: string, telegramUserId = 1508): Promise<TelegramEmulatorResponse> {
  return apiFetch("/v1/telegram/webhook", {
    method: "POST",
    body: JSON.stringify({
      message: {
        text: command,
        from: { id: telegramUserId, username: "local_wr3" },
        chat: { id: telegramUserId, type: "private" }
      }
    })
  });
}

export async function getBillingPlans(): Promise<BillingPlan[]> {
  return apiFetch("/v1/billing/plans");
}

export async function getLocalSubscription(user = "local-billing"): Promise<unknown> {
  return apiFetch("/v1/billing/subscription", {
    headers: { "x-wr3-user": user }
  });
}

export async function listDisclosureCases(): Promise<DisclosureCase[]> {
  return apiFetch("/v1/disclosure-cases", {
    headers: { "x-wr3-reviewer": "true" }
  });
}

export async function createDisclosureCase(input: {
  finding_id: string;
  project_contact: string;
  scope_note: string;
}): Promise<DisclosureCase> {
  return apiFetch("/v1/disclosure-cases", {
    method: "POST",
    headers: { "x-wr3-reviewer": "true" },
    body: JSON.stringify(input)
  });
}

export async function appendDisclosureContact(
  caseId: string,
  input: { channel: string; message: string }
): Promise<DisclosureCase> {
  return apiFetch(`/v1/disclosure-cases/${caseId}/contact-log`, {
    method: "POST",
    headers: { "x-wr3-reviewer": "true" },
    body: JSON.stringify(input)
  });
}

export async function advanceDisclosureCase(
  caseId: string,
  input: { status: string; note?: string }
): Promise<DisclosureCase> {
  return apiFetch(`/v1/disclosure-cases/${caseId}/advance`, {
    method: "POST",
    headers: { "x-wr3-reviewer": "true" },
    body: JSON.stringify(input)
  });
}
