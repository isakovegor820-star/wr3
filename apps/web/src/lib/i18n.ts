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
  triage_running: "ИИ-триаж",
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

export const scoreAxisLabels = {
  code_security_score: "Безопасность кода",
  centralization_score: "Централизация",
  liquidity_score: "Ликвидность",
  team_kyc_score: "Команда / KYC",
  behavior_score: "Поведение в сети"
} as const;

export const genericStatusLabels: Record<string, string> = {
  active: "активно",
  failed: "ошибка",
  installed: "установлено",
  missing_required: "нет обязательного инструмента",
  broken_required: "обязательный инструмент сломан",
  broken_optional: "необязательный инструмент сломан",
  skipped_optional: "необязательный инструмент пропущен",
  ready: "готово",
  partial: "частично готово",
  success: "успешно",
  skipped: "пропущено",
  not_started: "не запускалось",
  configured: "подключено",
  free_fallback: "бесплатный резерв",
  manual: "ручной режим",
  disabled: "выключено",
  blocked: "нужен внешний доступ",
  ready_for_localhost: "готово для localhost",
  needs_external_access: "нужен внешний доступ",
  private_contact_pending: "ожидает приватного контакта",
  seal_911_escalation: "эскалация в SEAL 911",
  cve_euvd_notice: "подготовка CVE/EUVD",
  limited_disclosure_allowed: "разрешено ограниченное раскрытие",
  full_disclosure_allowed: "разрешено полное раскрытие",
  resolved: "исправлено",
  closed: "закрыто"
};

export const scoreCapLabels: Record<string, string> = {
  confirmed_critical: "подтверждённая критичная находка",
  confirmed_high: "подтверждённая находка высокой важности",
  unverified_source: "исходный код не верифицирован",
  upgradeable_proxy_with_eoa_owner: "обновляемый прокси с EOA-владельцем",
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
  "No heuristic findings detected": "Эвристический проход не нашёл находок",
  "heuristic scan completed": "Эвристический скан завершён",
  "This does not mean the contract is safe; only that this MVP pass found no known pattern.":
    "Это не означает, что контракт безопасен; MVP-проход просто не нашёл известный паттерн.",
  "Run full static analysis, LLM triage, and human review before launch.":
    "Перед запуском проведите полный статический анализ, ИИ-триаж и ручное ревью.",
  "Unchecked Solana account requires owner and signer validation":
    "UncheckedAccount в Solana требует проверки owner и signer",
  "UncheckedAccount or AccountInfo usage detected": "Обнаружено использование UncheckedAccount или AccountInfo",
  "Unvalidated accounts can let callers substitute attacker-controlled accounts.":
    "Невалидированные аккаунты позволяют подставить account под контролем атакующего.",
  "Validate owner, signer, mutability, and expected PDA seeds for every unchecked account.":
    "Проверяйте владельца, подпись, mutability и ожидаемые PDA seeds для каждого unchecked account.",
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
  "No Solana heuristic findings detected": "Эвристический Solana-проход не нашёл находок",
  "Solana heuristic scan completed": "Эвристический Solana-скан завершён",
  "This does not mean the program is safe; Solana beta coverage is intentionally limited.":
    "Это не означает, что программа безопасна; покрытие Solana beta намеренно ограничено.",
  "Run Anchor tests, Trident fuzzing, and human review before deployment.":
    "Перед деплоем запустите Anchor-тесты, Trident-фаззинг и ручное ревью."
};

const limitationLabels: Record<string, string> = {
  demo_data: "демо-данные",
  anonymous_owner_token_required_for_private_access: "для приватного доступа нужен токен владельца",
  zdr_required_for_security_triage: "для security-триажа требуется ZDR-маршрут",
  openrouter_zdr_route_requested: "OpenRouter запрошен в ZDR-режиме",
  navy_route_requested: "NavyAI выбран как LLM-провайдер",
  navy_zdr_not_confirmed_using_configured_provider:
    "ZDR для NavyAI не подтверждён, используйте этот режим только для локальных/разрешённых проверок",
  navy_api_key_missing_using_deterministic_fallback:
    "NavyAI ключ не настроен, wr3 безопасно перешёл на детерминированный триаж",
  llm_triage_provider_error_using_deterministic_fallback:
    "ИИ-провайдер не ответил, wr3 безопасно перешёл на детерминированный триаж",
  llm_triage_disabled_using_deterministic_fallback: "ИИ-триаж выключен, используется детерминированный резерв",
  poc_requires_standard_or_deep_depth: "PoC требует стандартную или глубокую проверку",
  poc_no_high_or_critical_candidates: "нет находок высокой/критичной важности для PoC",
  poc_not_confirmed_after_retry_loop: "PoC не подтвердился после безопасных локальных попыток",
  foundry_binary_missing: "Foundry не установлен",
  proxy_admin_owner_extraction_requires_rpc_or_explorer_metadata:
    "для извлечения proxy admin/owner нужен RPC или дополнительные explorer-данные",
  high_risk_findings_require_human_review_before_public_claim:
    "находки высокого риска требуют ручного ревью перед публичным заявлением",
  public_page_redacts_private_findings: "публичная страница скрывает приватные находки",
  third_party_scan_public_poc_disabled: "для стороннего скана публичный PoC выключен",
  public_claims_require_human_review: "публичные заявления требуют ручного ревью",
  adversarial_input_detected: "обнаружены признаки prompt-injection",
  verified_source_pull_failed_upload_source: "не удалось подтянуть verified source, нужен исходный код"
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
    const source = value.replace("source_pulled_from_", "");
    const [explorer, chain, address] = source.split(":");
    return `исходный код подтянут из ${explorer}${chain ? ` (${chain})` : ""}${address ? ` для ${address.slice(0, 8)}...${address.slice(-6)}` : ""}`;
  }
  if (value.startsWith("llm_triage_provider_http_")) {
    const status = value.match(/http_(\d+)/)?.[1] ?? "ошибка";
    if (status === "403") {
      return "ИИ-провайдер отказал в доступе к модели, проверь доступ к Claude Opus 4.7";
    }
    if (status === "429") {
      return "ИИ-провайдер вернул лимит запросов, wr3 безопасно перешёл на детерминированный триаж";
    }
    return `ИИ-провайдер вернул HTTP ${status}, wr3 безопасно перешёл на детерминированный триаж`;
  }
  if (value.includes("_skipped:")) {
    const [engine, reason] = value.split("_skipped:");
    return `${engine} пропущен: ${reason}`;
  }
  if (value.includes("_raw_output_artifact_requires_encryption")) {
    return "для сохранения сырого вывода нужен ключ шифрования артефактов";
  }
  return value.replaceAll("_", " ");
}

export function tStatus(value: string): string {
  return genericStatusLabels[value] ?? value.replaceAll("_", " ");
}
