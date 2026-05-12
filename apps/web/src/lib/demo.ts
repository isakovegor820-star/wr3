import type { AuditSummary, Finding } from "@wr3/shared";

export const demoAudit: AuditSummary = {
  audit_id: "demo",
  state: "completed",
  chain: "base",
  address: "0x0000000000000000000000000000000000000000",
  tier: "free",
  progress: 100,
  score: {
    score_version: "wr3-score-v0.1",
    final_score: 69,
    code_security_score: 75,
    centralization_score: 59,
    liquidity_score: 80,
    team_kyc_score: 70,
    behavior_score: 80,
    caps_applied: ["unlimited_owner_mint"],
    weights: {
      code_security: 0.35,
      centralization: 0.2,
      liquidity: 0.15,
      team_kyc: 0.15,
      behavior: 0.15
    }
  },
  limitations: ["demo_data", "poc_requires_paid_tier"],
  failed_stages: [],
  engine_version: "wr3-engine-v0.1",
  score_version: "wr3-score-v0.1",
  source_metadata: {
    source_hash: "demo",
    source_origin: "pasted",
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
  },
  retention_until: null,
  adversarial_input_detected: false,
  access: {
    is_owner: true,
    is_public_view: false,
    can_view_private_findings: true,
    can_view_raw_outputs: false,
    auth_provider: "demo"
  }
};

export const demoFindings: Finding[] = [
  {
    id: "wr3-find-demo-1",
    audit_id: "demo",
    chain: "base",
    contract: {
      address: "0x0000000000000000000000000000000000000000",
      name: "Vault",
      file: "Contract.sol"
    },
    location: {
      file: "Contract.sol",
      start_line: null,
      end_line: null,
      function: null
    },
    taxonomy: {
      swc: null,
      cwe: null,
      wr3_category: "centralization"
    },
    severity: "low",
    confidence: 0.76,
    exploitability: "unknown",
    sources: ["wr3_heuristic_evm"],
    evidence: {
      static_trace: "обнаружен паттерн onlyOwner mint",
      poc_status: "not_attempted",
      poc_artifact_uri: null,
      fuzzer_counterexample_uri: null
    },
    summary: "Mint под контролем владельца влияет на централизацию",
    description: "Обнаружен owner mint pattern",
    impact: "Привилегированный владелец может менять предположения о supply.",
    recommendation: "Задокументируйте лимиты mint, используйте multisig или добавьте неизменяемые caps.",
    dismissal_reason: null,
    human_review_status: "not_required"
  }
];
