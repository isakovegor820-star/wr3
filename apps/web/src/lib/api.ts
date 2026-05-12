import type { AuditSummary, Chain, Finding, ScoreBreakdown } from "@wr3/shared";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export type CreateAuditInput = {
  chain: Chain;
  address: string;
  source: string;
  allow_bytecode_only?: boolean;
  requested_depth: "preliminary" | "standard" | "deep";
  visibility: "private" | "public";
  user_intent: "pre_launch_self_check" | "third_party_research" | "monitoring";
};

export type PublicProjectSummary = {
  chain: Chain;
  address: string;
  score: ScoreBreakdown | null;
  safe_harbor_status: boolean;
  public_findings: Finding[];
  limitations: string[];
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

function accessHeaders(ownerToken?: string): Record<string, string> {
  return ownerToken ? { "x-wr3-owner-token": ownerToken } : {};
}

function withOwnerToken(path: string, ownerToken?: string): string {
  if (!ownerToken) {
    return path;
  }
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}owner_token=${encodeURIComponent(ownerToken)}`;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
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

export async function createAudit(input: CreateAuditInput): Promise<CreateAuditResponse> {
  return apiFetch("/v1/audits", {
    method: "POST",
    body: JSON.stringify({
      ...input,
      address: input.address || null,
      source: input.source || null
    })
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
  const response = await fetch(`${API_BASE}${withOwnerToken(`/v1/audits/${id}/report`, ownerToken)}`, {
    cache: "no-store",
    headers: accessHeaders(ownerToken)
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.text();
}

export async function requestEmailSession(email: string) {
  return apiFetch("/v1/auth/email/request-link", {
    method: "POST",
    body: JSON.stringify({ email })
  });
}

export async function getPublicProject(chain: Chain, address: string): Promise<PublicProjectSummary> {
  return apiFetch(`/v1/projects/${chain}/${address}`);
}
