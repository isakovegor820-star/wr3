# wr3 Local 24/7 Scout

Этот режим нужен, чтобы wr3 сам брал публичные адреса из бесплатного источника, ставил их в пассивный аудит и создавал рабочую очередь кандидатов.

## Источник целей

MVP использует бесплатный API DeFiLlama:

- `https://api.llama.fi/protocols`
- API key не нужен.
- wr3 берёт только поддерживаемые сети: Ethereum, Base, BSC, Arbitrum, Solana beta.
- CEX и неподдерживаемые сети отфильтровываются.

Важно: `address` в DeFiLlama может быть token address или protocol pointer, а не главный contract проекта. Поэтому wr3 показывает это как цель для пассивного анализа, а не как доказанную уязвимость.

## Локальный запуск

Сначала подними API и web:

```bash
npm run dev:local
```

В другом терминале запусти один проход:

```bash
npm run scout:once
```

Или локальный 24/7 loop:

```bash
npm run scout:loop
```

По умолчанию loop раз в 15 минут работает как all-network cycle:

1. берёт цели из DeFiLlama;
2. проходит по Base / Ethereum / BSC / Arbitrum / Solana beta;
3. создаёт приватные deep audit jobs;
4. складывает результаты в review queue;
5. печатает ссылки на отчёты с owner token.

## Настройки

```bash
WR3_SCOUT_API_BASE=http://127.0.0.1:8001
WR3_SCOUT_INTERVAL_SECONDS=900
WR3_SCOUT_LIMIT=5
WR3_SCOUT_MIN_TVL_USD=1000000
WR3_SCOUT_CHAINS=base,ethereum,bsc,arbitrum,solana
WR3_SCOUT_DEPTH=deep
WR3_SCOUT_TIER=team
```

Если нужен старый одиночный режим, запускай:

```bash
python3 scripts/scout_loop.py --once --single-source
```

## Что wr3 делает

- Берёт публичные адреса протоколов.
- Запускает passive scan.
- Показывает findings, confidence, readiness и evidence gaps.
- Даёт черновик приватного обращения, когда сигнал достаточно готов.
- Делит отчёты на очереди: `можно писать`, `проверить вручную`, `пропустить`.
- Подсказывает, где искать security contact: сайт, `security.txt`, GitHub SECURITY.md, bounty-платформы.

## Что wr3 не делает

- Не отправляет сообщения в поддержку автоматически.
- Не делает mainnet-транзакции.
- Не публикует обвинения.
- Не считает heuristic-only сигнал готовым багом.
- Не выдаёт DeFiLlama address за подтверждённый scope без ручной проверки.
