import { z } from "zod";

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

export type Chain = (typeof chains)[number];
export type AuditState = (typeof auditStates)[number];
export type Severity = (typeof severities)[number];
export type Exploitability = (typeof exploitabilities)[number];
export type Tier = (typeof tiers)[number];

export const contractRefSchema = z.object({
  address: z.string().nullable(),
  name: z.string(),
  file: z.string().nullable()
});

export const findingSchema = z.object({
  id: z.string(),
  audit_id: z.string(),
  chain: z.enum(chains),
  contract: contractRefSchema,
  location: z.object({
    file: z.string().nullable(),
    start_line: z.number().int().positive().nullable(),
    end_line: z.number().int().positive().nullable(),
    function: z.string().nullable()
  }),
  taxonomy: z.object({
    swc: z.string().nullable(),
    cwe: z.string().nullable(),
    wr3_category: z.string()
  }),
  severity: z.enum(severities),
  confidence: z.number().min(0).max(1),
  exploitability: z.enum(exploitabilities),
  sources: z.array(z.string()),
  evidence: z.object({
    static_trace: z.string().nullable(),
    poc_status: z.enum(["not_attempted", "failed", "confirmed"]),
    poc_artifact_uri: z.string().nullable(),
    fuzzer_counterexample_uri: z.string().nullable()
  }),
  summary: z.string(),
  description: z.string(),
  impact: z.string(),
  recommendation: z.string(),
  dismissal_reason: z.string().nullable(),
  human_review_status: z.enum(["not_required", "pending", "approved", "rejected"])
});

export type Finding = z.infer<typeof findingSchema>;

export const scoreBreakdownSchema = z.object({
  score_version: z.string(),
  final_score: z.number().min(0).max(100),
  code_security_score: z.number().min(0).max(100),
  centralization_score: z.number().min(0).max(100),
  liquidity_score: z.number().min(0).max(100),
  team_kyc_score: z.number().min(0).max(100),
  behavior_score: z.number().min(0).max(100),
  caps_applied: z.array(z.string()),
  weights: z.object({
    code_security: z.number(),
    centralization: z.number(),
    liquidity: z.number(),
    team_kyc: z.number(),
    behavior: z.number()
  })
});

export type ScoreBreakdown = z.infer<typeof scoreBreakdownSchema>;

export const proxyInfoSchema = z.object({
  is_proxy: z.boolean(),
  proxy_type: z.string().nullable(),
  implementation_address: z.string().nullable(),
  admin_address: z.string().nullable(),
  owner_hint: z.string().nullable(),
  eoa_admin_possible: z.boolean(),
  detection_sources: z.array(z.string()),
  limitations: z.array(z.string())
});

export const sourceMetadataSchema = z.object({
  source_hash: z.string().nullable(),
  source_origin: z.string(),
  verified_at: z.string().nullable(),
  explorer_url: z.string().nullable(),
  explorer_metadata: z.record(z.unknown()),
  bytecode_only: z.boolean(),
  proxy_info: proxyInfoSchema
});

export const auditSummarySchema = z.object({
  audit_id: z.string(),
  state: z.enum(auditStates),
  chain: z.enum(chains),
  address: z.string().nullable(),
  tier: z.enum(tiers),
  progress: z.number().min(0).max(100),
  score: scoreBreakdownSchema.nullable(),
  limitations: z.array(z.string()),
  failed_stages: z.array(z.string()),
  engine_version: z.string(),
  score_version: z.string(),
  source_metadata: sourceMetadataSchema.default({
    source_hash: null,
    source_origin: "unknown",
    verified_at: null,
    explorer_url: null,
    explorer_metadata: {},
    bytecode_only: false,
    proxy_info: {
      is_proxy: false,
      proxy_type: null,
      implementation_address: null,
      admin_address: null,
      owner_hint: null,
      eoa_admin_possible: false,
      detection_sources: [],
      limitations: []
    }
  }),
  retention_until: z.string().nullable().default(null),
  adversarial_input_detected: z.boolean().default(false)
});

export type AuditSummary = z.infer<typeof auditSummarySchema>;
