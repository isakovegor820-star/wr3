import { z } from "zod";
import {
  auditStates,
  chains,
  exploitabilities,
  humanReviewStatuses,
  pocStatuses,
  requestedDepths,
  severities,
  tiers,
  userIntents,
  visibilities
} from "./enums.js";

export const contractRefSchema = z.object({
  address: z.string().nullable(),
  name: z.string(),
  file: z.string().nullable()
});

export const sourceLocationSchema = z.object({
  file: z.string().nullable(),
  start_line: z.number().int().positive().nullable(),
  end_line: z.number().int().positive().nullable(),
  function: z.string().nullable()
});

export const taxonomySchema = z.object({
  swc: z.string().nullable(),
  cwe: z.string().nullable(),
  wr3_category: z.string()
});

export const evidenceSchema = z.object({
  static_trace: z.string().nullable(),
  poc_status: z.enum(pocStatuses),
  poc_artifact_uri: z.string().nullable(),
  fuzzer_counterexample_uri: z.string().nullable()
});

export const disclosureAssessmentSchema = z.object({
  verdict: z.string(),
  verdict_label: z.string(),
  readiness: z.string(),
  readiness_label: z.string(),
  can_contact_support: z.boolean(),
  false_positive_risk: z.string(),
  plain_explanation: z.string(),
  technical_explanation: z.string(),
  next_step: z.string(),
  manual_checklist: z.array(z.string()),
  evidence_gaps: z.array(z.string()),
  location_status: z.string(),
  location_label: z.string()
});

export const findingSchema = z.object({
  id: z.string(),
  audit_id: z.string(),
  chain: z.enum(chains),
  contract: contractRefSchema,
  location: sourceLocationSchema,
  taxonomy: taxonomySchema,
  severity: z.enum(severities),
  confidence: z.number().min(0).max(1),
  exploitability: z.enum(exploitabilities),
  sources: z.array(z.string()),
  evidence: evidenceSchema,
  summary: z.string(),
  description: z.string(),
  impact: z.string(),
  recommendation: z.string(),
  dismissal_reason: z.string().nullable(),
  human_review_status: z.enum(humanReviewStatuses),
  disclosure_assessment: disclosureAssessmentSchema.default({
    verdict: "too_early",
    verdict_label: "Рано писать",
    readiness: "signal",
    readiness_label: "Сигнал",
    can_contact_support: false,
    false_positive_risk: "high",
    plain_explanation: "Это предварительный сигнал. Перед обращением нужна ручная проверка.",
    technical_explanation: "Детали ещё не рассчитаны.",
    next_step: "Проверить сигнал вручную и собрать доказательства.",
    manual_checklist: [],
    evidence_gaps: [],
    location_status: "unknown",
    location_label: "Точное место не определено"
  })
});

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

export const auditAccessSummarySchema = z.object({
  is_owner: z.boolean(),
  is_public_view: z.boolean(),
  can_view_private_findings: z.boolean(),
  can_view_raw_outputs: z.boolean(),
  auth_provider: z.string().nullable()
});

export const securityAgentSummarySchema = z.object({
  provider: z.string(),
  model: z.string(),
  status: z.string(),
  status_label: z.string(),
  provider_invoked: z.boolean(),
  fallback: z.string(),
  error_type: z.string().nullable(),
  agent_roles: z.array(z.string()),
  agent_payloads_received: z.array(z.string()),
  zdr_required: z.boolean(),
  prompt_wrapped_untrusted_source: z.boolean(),
  explanation: z.string(),
  recommendation: z.string()
});

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

export const auditInputSchema = z.object({
  chain: z.enum(chains),
  address: z.string().nullable(),
  source: z.string().nullable(),
  allow_bytecode_only: z.boolean().default(false),
  requested_depth: z.enum(requestedDepths),
  visibility: z.enum(visibilities),
  user_intent: z.enum(userIntents),
  tier: z.enum(tiers).default("free")
});

export const normalizedSourceSchema = z.object({
  chain: z.enum(chains),
  address: z.string().nullable(),
  source: z.string(),
  source_hash: z.string(),
  verified: z.boolean(),
  contract_name: z.string(),
  file_name: z.string(),
  limitations: z.array(z.string())
});

export const artifactSchema = z.object({
  id: z.string(),
  audit_id: z.string(),
  kind: z.enum(["raw_output", "report", "poc", "fuzzer_counterexample", "manifest"]),
  uri: z.string(),
  private: z.boolean(),
  encryption_key_ref: z.string().nullable(),
  retention_until: z.string().nullable()
});

export const engineRunResultSchema = z.object({
  engine: z.string(),
  status: z.enum(["success", "partial", "failed", "skipped"]),
  duration_ms: z.number().int().nonnegative(),
  findings: z.array(findingSchema),
  artifacts: z.array(artifactSchema),
  raw_output: z.string().nullable(),
  error: z.string().nullable(),
  versions: z.record(z.string())
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
  static_analysis_status: z.string().default("not_started"),
  security_agent: securityAgentSummarySchema.default({
    provider: "disabled",
    model: "local-deterministic-triage",
    status: "not_started",
    status_label: "ИИ-агент ещё не запускался",
    provider_invoked: false,
    fallback: "not_started",
    error_type: null,
    agent_roles: [],
    agent_payloads_received: [],
    zdr_required: true,
    prompt_wrapped_untrusted_source: false,
    explanation: "Пока findings создают статические инструменты и локальные эвристики.",
    recommendation: "Для глубокого режима подключи защищённую ZDR/local модель в WR3_LLM_MODEL."
  }),
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
  adversarial_input_detected: z.boolean().default(false),
  access: auditAccessSummarySchema.default({
    is_owner: false,
    is_public_view: false,
    can_view_private_findings: false,
    can_view_raw_outputs: false,
    auth_provider: null
  })
});

export type ContractRef = z.infer<typeof contractRefSchema>;
export type SourceLocation = z.infer<typeof sourceLocationSchema>;
export type Taxonomy = z.infer<typeof taxonomySchema>;
export type Evidence = z.infer<typeof evidenceSchema>;
export type DisclosureAssessment = z.infer<typeof disclosureAssessmentSchema>;
export type Finding = z.infer<typeof findingSchema>;
export type ScoreBreakdown = z.infer<typeof scoreBreakdownSchema>;
export type AuditAccessSummary = z.infer<typeof auditAccessSummarySchema>;
export type SecurityAgentSummary = z.infer<typeof securityAgentSummarySchema>;
export type ProxyInfo = z.infer<typeof proxyInfoSchema>;
export type SourceMetadata = z.infer<typeof sourceMetadataSchema>;
export type AuditInput = z.infer<typeof auditInputSchema>;
export type NormalizedSource = z.infer<typeof normalizedSourceSchema>;
export type Artifact = z.infer<typeof artifactSchema>;
export type EngineRunResult = z.infer<typeof engineRunResultSchema>;
export type AuditSummary = z.infer<typeof auditSummarySchema>;
