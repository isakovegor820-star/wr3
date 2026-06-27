export interface ChainOption {
  value: 'eth' | 'base' | 'bsc' | 'arb' | 'sol';
  label: string;
  short: string;
}

export const CHAINS: ChainOption[] = [
  { value: 'eth', label: 'Ethereum', short: 'ETH' },
  { value: 'base', label: 'Base', short: 'BASE' },
  { value: 'bsc', label: 'BSC', short: 'BSC' },
  { value: 'arb', label: 'Arbitrum', short: 'ARB' },
  { value: 'sol', label: 'Solana (beta)', short: 'SOL' },
];

export const TARGET_PLACEHOLDER = '0x… или вставьте код';

export const SCAN_DEPTH_OPTIONS = [
  { value: 'fast', label: 'Быстрый', time: '~3 мин' },
  { value: 'deep', label: 'Глубокий', time: '~15 мин' },
] as const;

export const TRUST_GUARANTEES = [
  {
    icon: 'lock',
    title: 'Локально и приватно',
    description:
      'Статический анализ (Slither, Aderyn, Wake) выполняется локально. Приватные артефакты шифруются.',
  },
  {
    icon: 'shield',
    title: 'ZDR-маршрут для LLM',
    description:
      'Мульти-агентный ИИ-триаж идёт по Zero Data Retention маршруту. Находки не передаются третьим сторонам.',
  },
  {
    icon: 'ban',
    title: 'Без mainnet, без --ffi',
    description:
      'PoC и фаззинг выполняются только в песочнице. Safety-границы — это фича, а не ограничение.',
  },
  {
    icon: 'eye',
    title: 'Провенанс и доказательства',
    description:
      'Каждая находка содержит источник, оценку эксплуатабельности и честный список того, что ещё не доказано.',
  },
] as const;

export const WHAT_YOU_GET = [
  {
    id: 'transparent-scoring',
    icon: 'gauge',
    title: 'Прозрачный wr3-score',
    description:
      'Детерминированный скоринг с открытыми весами. Никаких чёрных ящиков и pay-to-pass бейджей. Вы видите, какие находки повлияли на итог.',
    tag: 'Качество',
    accent: 'primary',
  },
  {
    id: 'evidence-first',
    icon: 'file-search',
    title: 'Доказательства, а не ярлыки',
    description:
      'Каждая находка: источник (Slither/Aderyn/Wake), оценка эксплуатабельности, PoC-статус и честный список «что ещё не доказано».',
    tag: 'Качество',
    accent: 'success',
  },
  {
    id: 'safety-bounds',
    icon: 'shield',
    title: 'Safety-границы как фича',
    description:
      'PoC и фаззинг только в песочнице. Без mainnet, без --ffi. Приватные артефакты шифруются. LLM-триаж по ZDR-маршруту.',
    tag: 'Качество',
    accent: 'warning',
  },
  {
    id: 'one-action',
    icon: 'zap',
    title: 'Скан в одно действие',
    description:
      'Вставил адрес или код — получил результат. Понятная навигация: командный центр, дашборд сканов, публичная карточка проекта.',
    tag: 'Удобство',
    accent: 'primary',
  },
  {
    id: 'next-step',
    icon: 'compass',
    title: 'Чёткий следующий шаг',
    description:
      'wr3 не оставляет вас с цифрой. Для каждой находки — что проверить, какой следующий шаг безопасен, что требует ревью.',
    tag: 'Удобство',
    accent: 'success',
  },
  {
    id: 'responsible-disclosure',
    icon: 'megaphone',
    title: 'Ответственное раскрытие',
    description:
      'Человек подтверждает выводы и раскрытие. Платформа не делает публичных обвинений. Нет ярлыков scam/fraud — только доказательства.',
    tag: 'Удобство',
    accent: 'info',
  },
] as const;

export const PIPELINE_STEPS = [
  {
    id: 'ingest',
    title: 'Ингест',
    description:
      'Нормализация Solidity/Vyper байткода и исходного кода. Разрешение импортов, AST, метаданные компилятора.',
    icon: 'download',
    tools: 'Etherscan · Sourcify · RPC',
  },
  {
    id: 'static',
    title: 'Статический анализ',
    description:
      'Детерминированный прогон набора статических анализаторов с нормализацией результатов и дедупликацией.',
    icon: 'search',
    tools: 'Slither · Aderyn · Wake',
  },
  {
    id: 'ai-triage',
    title: 'Мульти-агентный ИИ-триаж',
    description:
      'Независимые агенты: severity, false-positive, business-logic, cross-contract. Консенсус по приоритету находок.',
    icon: 'cpu',
    tools: 'ZDR-маршрут · приватно',
  },
  {
    id: 'poc',
    title: 'PoC / фаззинг в песочнице',
    description:
      'Попытка воспроизвести находку в изолированной среде. Только песочница — без mainnet и --ffi.',
    icon: 'flask-conical',
    tools: 'Foundry · Echidna',
  },
  {
    id: 'scoring',
    title: 'wr3-score',
    description:
      'Детерминированный скоринг по открытым весам. Каждая находка трассируется до финальной оценки.',
    icon: 'gauge',
    tools: 'Открытые веса',
  },
  {
    id: 'report',
    title: 'Отчёт + очередь ревью',
    description:
      'Структурированный отчёт с провенансом. Доставка в командный центр и Telegram. Человек подтверждает выводы.',
    icon: 'file-check',
    tools: 'JSON · Markdown · Telegram',
  },
] as const;

export const NOT_WR3 = [
  {
    title: 'Не гарантия «secure»',
    description:
      'wr3-score — это сигнал риска, а не сертификат безопасности. Высокий score не означает отсутствие уязвимостей.',
  },
  {
    title: 'Не страховка',
    description:
      'wr3 не покрывает потери и не заменяет страхование рисков. Это инструмент пред-аудита, а не финансовая защита.',
  },
  {
    title: 'Не эксплуатация mainnet',
    description:
      'PoC и фаззинг выполняются только в песочнице. wr3 не взаимодействует с mainnet и не выполняет эксплойты.',
  },
  {
    title: 'Не публичные обвинения',
    description:
      'wr3 не ставит ярлыки scam/fraud. Только доказательства, провенанс и ответственное раскрытие.',
  },
  {
    title: 'Не замена энтерпрайз-аудиту',
    description:
      'Сolo-команды и небольшие проекты получают быстрый сигнал. Для production-grade систем — полноценный аудит остаётся обязательным.',
  },
];
