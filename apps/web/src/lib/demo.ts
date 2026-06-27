import type { AuditSummary, Finding } from "@wr3/shared";

export const demoAudit: AuditSummary = {
  audit_id: "demo",
  state: "completed",
  chain: "base",
  address: "0x0000000000000000000000000000000000000000",
  tier: "pro",
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
  limitations: ["demo_data"],
  failed_stages: [],
  engine_version: "wr3-engine-v0.1",
  score_version: "wr3-score-v0.1",
  static_analysis_status: "success",
  security_agent: {
    provider: "disabled",
    model: "local-deterministic-triage",
    status: "disabled",
    status_label: "ИИ-агент не запускался",
    provider_invoked: false,
    fallback: "deterministic",
    error_type: null,
    agent_roles: ["severity_classifier", "false_positive_filter", "business_logic_reasoner", "cross_contract_analyzer"],
    agent_payloads_received: [],
    zdr_required: true,
    prompt_wrapped_untrusted_source: true,
    explanation: "Демо-находку создал fixture detector. ИИ в этом демо не подтверждал сигнал.",
    recommendation: "Для реального глубокого triage подключи OpenRouter ZDR или локальную модель через WR3_LLM_MODEL."
  },
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
    human_review_status: "not_required",
    disclosure_assessment: {
      verdict: "too_early",
      verdict_label: "Рано писать",
      readiness: "signal",
      readiness_label: "Сигнал",
      can_contact_support: false,
      false_positive_risk: "high",
      plain_explanation:
        "wr3 увидел owner mint pattern. Это кандидатный сигнал, а не подтверждённая уязвимость: нужно проверить роли, supply cap и официальный scope.",
      technical_explanation:
        "Категория: centralization. Источник: wr3_heuristic_evm. Location missing; PoC не запускался; exploitability unknown.",
      next_step: "Найти точное место в коде, проверить owner/admin и подтвердить impact перед любым письмом.",
      manual_checklist: [
        "Проверить, есть ли immutable cap или лимит mint.",
        "Проверить owner/admin и multisig.",
        "Проверить, входит ли токен в scope программы."
      ],
      evidence_gaps: [
        "Нет точной location.",
        "Нет PoC/fork-test подтверждения.",
        "Сигнал найден только heuristic detector."
      ],
      location_status: "missing",
      location_label: "Точное место не определено"
    }
  }
];
