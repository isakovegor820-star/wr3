export const chains = ["ethereum", "base", "bsc", "arbitrum", "solana"] as const;
export const auditStates = [
  "created",
  "queued",
  "ingesting",
  "needs_source",
  "static_running",
  "triage_running",
  "poc_running",
  "fuzzing_running",
  "scoring",
  "human_review",
  "changes_requested",
  "partial",
  "completed",
  "failed",
  "retrying",
  "rejected",
  "terminal"
] as const;
export const severities = ["critical", "high", "medium", "low", "info"] as const;
export const exploitabilities = ["confirmed", "likely", "theoretical", "unknown", "dismissed"] as const;
export const tiers = ["free", "hobby", "team", "pro"] as const;
export const requestedDepths = ["preliminary", "standard", "deep"] as const;
export const visibilities = ["private", "public"] as const;
export const userIntents = ["pre_launch_self_check", "third_party_research", "monitoring"] as const;
export const humanReviewStatuses = ["not_required", "pending", "approved", "rejected"] as const;
export const pocStatuses = ["not_attempted", "failed", "confirmed"] as const;

export type Chain = (typeof chains)[number];
export type AuditState = (typeof auditStates)[number];
export type Severity = (typeof severities)[number];
export type Exploitability = (typeof exploitabilities)[number];
export type Tier = (typeof tiers)[number];
export type RequestedDepth = (typeof requestedDepths)[number];
export type Visibility = (typeof visibilities)[number];
export type UserIntent = (typeof userIntents)[number];
export type HumanReviewStatus = (typeof humanReviewStatuses)[number];
export type PocStatus = (typeof pocStatuses)[number];
