import type { AuditState, Chain, Finding } from "@wr3/shared";

export const chainLabels: Record<Chain, string> = {
  ethereum: "Ethereum",
  base: "Base",
  bsc: "BSC",
  arbitrum: "Arbitrum",
  solana: "Solana beta"
};

export const auditStateLabels: Record<AuditState, string> = {
  created: "создан",
  queued: "в очереди",
  ingesting: "загрузка исходников",
  needs_source: "нужен исходный код",
  static_running: "статический анализ",
  triage_running: "AI-триаж",
  poc_running: "PoC-проверка",
  fuzzing_running: "фаззинг",
  scoring: "скоринг",
  human_review: "ручное ревью",
  changes_requested: "нужны правки",
  partial: "частично готово",
  completed: "готово",
  failed: "ошибка",
  retrying: "повтор",
  rejected: "отклонено",
  terminal: "завершено"
};

export const severityLabels: Record<Finding["severity"], string> = {
  critical: "критично",
  high: "высокий",
  medium: "средний",
  low: "низкий",
  info: "инфо"
};

export const exploitabilityLabels: Record<Finding["exploitability"], string> = {
  confirmed: "подтверждено",
  likely: "вероятно",
  theoretical: "теоретически",
  unknown: "неизвестно",
  dismissed: "отклонено"
};

export const scoreCapLabels: Record<string, string> = {
  confirmed_critical: "подтверждённая критичная находка",
  confirmed_high: "подтверждённая находка высокой важности",
  unverified_source: "исходный код не верифицирован",
  upgradeable_proxy_with_eoa_owner: "обновляемый proxy с EOA-владельцем",
  unlimited_owner_mint: "неограниченный mint у владельца"
};

const findingText: Record<string, string> = {
  "Authorization depends on tx.origin": "Авторизация зависит от tx.origin",
  "tx.origin usage detected": "Обнаружено использование tx.origin",
  "Phishing flows can pass authorization through an intermediate caller.":
    "Фишинговый сценарий может пройти авторизацию через промежуточный контракт.",
  "Use msg.sender based authorization and explicit role checks.":
    "Используйте авторизацию через msg.sender и явные проверки ролей.",
  "Delegatecall requires strict target control": "Delegatecall требует строгого контроля target-адреса",
  "delegatecall usage detected": "Обнаружено использование delegatecall",
  "A controlled or unvalidated delegatecall target can modify caller storage.":
    "Контролируемый или непроверенный delegatecall target может менять storage вызывающего контракта.",
  "Restrict delegatecall targets and validate implementation code hashes.":
    "Ограничьте delegatecall targets и проверяйте хэши кода implementation.",
  "Low-level value transfer needs reentrancy review": "Low-level value transfer требует проверки reentrancy",
  "low-level call with value pattern detected": "Обнаружен low-level call с value",
  "External calls before state updates can enable reentrant accounting bugs.":
    "Внешние вызовы до обновления состояния могут открыть reentrancy-баги в учёте.",
  "Use checks-effects-interactions and a reentrancy guard where appropriate.":
    "Используйте checks-effects-interactions и reentrancy guard там, где это уместно.",
  "Selfdestruct path is present": "В коде есть selfdestruct-путь",
  "selfdestruct usage detected": "Обнаружено использование selfdestruct",
  "Contract lifecycle controls may permanently remove code or alter assumptions.":
    "Контроль жизненного цикла может навсегда удалить код или изменить системные предположения.",
  "Remove selfdestruct unless it is explicitly required and access-controlled.":
    "Удалите selfdestruct, если он явно не нужен и не закрыт access-control.",
  "Owner-controlled mint path affects token centralization": "Mint под контролем владельца влияет на централизацию",
  "onlyOwner mint function pattern detected": "Обнаружен паттерн onlyOwner mint",
  "A privileged owner may be able to change supply assumptions.":
    "Привилегированный владелец может менять предположения о supply.",
  "Document mint limits, use multisig ownership, or add immutable caps.":
    "Задокументируйте лимиты mint, используйте multisig или добавьте неизменяемые caps.",
  "No heuristic findings detected": "Heuristic-проход не нашёл находок",
  "heuristic scan completed": "Heuristic-скан завершён",
  "This does not mean the contract is safe; only that this MVP pass found no known pattern.":
    "Это не означает, что контракт безопасен; MVP-проход просто не нашёл известный паттерн.",
  "Run full static analysis, LLM triage, and human review before launch.":
    "Перед запуском проведите полный static analysis, LLM-триаж и human review.",
  "Unchecked Solana account requires owner and signer validation":
    "UncheckedAccount в Solana требует проверки owner и signer",
  "UncheckedAccount or AccountInfo usage detected": "Обнаружено использование UncheckedAccount или AccountInfo",
  "Unvalidated accounts can let callers substitute attacker-controlled accounts.":
    "Невалидированные аккаунты позволяют подставить account под контролем атакующего.",
  "Validate owner, signer, mutability, and expected PDA seeds for every unchecked account.":
    "Проверяйте owner, signer, mutability и ожидаемые PDA seeds для каждого unchecked account.",
  "init_if_needed can enable account reinitialization footguns":
    "init_if_needed может привести к ошибкам reinitialization",
  "init_if_needed constraint detected": "Обнаружен constraint init_if_needed",
  "Reinitialization mistakes can reset state or bypass intended one-time setup.":
    "Ошибки reinitialization могут сбросить state или обойти одноразовую инициализацию.",
  "Add explicit initialization state checks and document why init_if_needed is required.":
    "Добавьте явные проверки состояния инициализации и объясните, зачем нужен init_if_needed.",
  "Signed CPI path needs explicit PDA seed review": "Signed CPI требует явного ревью PDA seeds",
  "invoke_signed detected without obvious seed constraints in source slice":
    "Обнаружен invoke_signed без очевидных seed constraints в данном фрагменте кода",
  "Incorrect PDA seed validation can authorize unintended program actions.":
    "Неверная проверка PDA seeds может авторизовать нежелательные действия программы.",
  "Ensure PDA seeds, bumps, and account constraints are explicit and tested.":
    "Убедитесь, что PDA seeds, bumps и account constraints явные и покрыты тестами.",
  "No Solana heuristic findings detected": "Solana heuristic-проход не нашёл находок",
  "Solana heuristic scan completed": "Solana heuristic-скан завершён",
  "This does not mean the program is safe; Solana beta coverage is intentionally limited.":
    "Это не означает, что программа безопасна; покрытие Solana beta намеренно ограничено.",
  "Run Anchor tests, Trident fuzzing, and human review before deployment.":
    "Перед деплоем запустите Anchor tests, Trident fuzzing и human review."
};

const limitationLabels: Record<string, string> = {
  demo_data: "демо-данные",
  poc_requires_paid_tier: "PoC доступен только на платном тарифе",
  anonymous_owner_token_required_for_private_access: "для приватного доступа нужен owner-token",
  zdr_required_for_security_triage: "для security-триажа требуется ZDR-маршрут",
  llm_triage_disabled_using_deterministic_fallback: "LLM-триаж выключен, используется deterministic fallback",
  poc_requires_standard_or_deep_depth: "PoC требует standard/deep глубину скана",
  poc_no_high_or_critical_candidates: "нет находок высокой/критичной важности для PoC",
  foundry_binary_missing: "Foundry не установлен",
  high_risk_findings_require_human_review_before_public_claim:
    "high-risk находки требуют human review перед публичным claim",
  public_page_redacts_private_findings: "публичная страница скрывает приватные находки",
  third_party_scan_public_poc_disabled: "для third-party скана публичный PoC выключен",
  public_claims_require_human_review: "публичные claims требуют human review",
  adversarial_input_detected: "обнаружены признаки prompt-injection",
  verified_source_pull_failed_upload_source: "не удалось подтянуть verified source, нужен исходный код",
  raw_outputs_require_paid_tier_artifact_access: "сырые выводы требуют платный owner-доступ"
};

export function tFindingText(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  return findingText[value] ?? value;
}

export function tCap(value: string): string {
  return scoreCapLabels[value] ?? value;
}

export function tLimitation(value: string): string {
  if (limitationLabels[value]) {
    return limitationLabels[value];
  }
  if (value.startsWith("source_pulled_from_")) {
    return `исходный код подтянут из ${value.replace("source_pulled_from_", "")}`;
  }
  if (value.includes("_skipped:")) {
    const [engine, reason] = value.split("_skipped:");
    return `${engine} пропущен: ${reason}`;
  }
  if (value.includes("_raw_output_artifact_requires_encryption")) {
    return "для сохранения сырого вывода нужен ключ шифрования artifacts";
  }
  if (value.includes("_billing_verification_stub")) {
    return "billing-проверка тарифа пока работает в MVP-режиме";
  }
  return value.replaceAll("_", " ");
}
