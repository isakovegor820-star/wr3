import { Logo, Wordmark } from './logo';

const footerSections = [
  {
    title: 'Платформа',
    links: [
      { label: 'Командный центр', href: '/command' },
      { label: 'Дашборд сканов', href: '/dashboard' },
      { label: 'Публичная карточка', href: '#top' },
      { label: 'Telegram-бот', href: '/tg' },
    ],
  },
  {
    title: 'Как это работает',
    links: [
      { label: 'Что внутри', href: '#what-inside' },
      { label: 'Конвейер аудита', href: '#how-it-works' },
      { label: 'Scout 24/7', href: '#scout' },
      { label: 'Доставка в Telegram', href: '#scout' },
    ],
  },
  {
    title: 'Гарантии',
    links: [
      { label: 'Локально и приватно', href: '#what-inside' },
      { label: 'ZDR-маршрут LLM', href: '#what-inside' },
      { label: 'Safety-границы', href: '#what-inside' },
      { label: 'Честные границы', href: '#verify-address' },
    ],
  },
];

const supportedChains = ['Ethereum', 'Base', 'BSC', 'Arbitrum', 'Solana (beta)'];

export function Footer() {
  return (
    <footer className="relative border-t border-border bg-background" aria-labelledby="footer-heading">
      <h2 id="footer-heading" className="sr-only">
        Подвал
      </h2>
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[1.2fr_2fr]">
          {/* Brand */}
          <div>
            <a
              href="#top"
              className="flex items-center gap-2.5"
              aria-label="wr3 — главная"
            >
              <Logo size={32} />
              <Wordmark className="text-xl" />
            </a>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground text-pretty">
              AI-ассистированная платформа пред-аудита и триажа рисков
              смарт-контрактов. Safety-first.
            </p>
            <div className="mt-5">
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground-soft">
                Поддерживаемые сети
              </p>
              <div className="flex flex-wrap gap-1.5">
                {supportedChains.map((c) => (
                  <span
                    key={c}
                    className="rounded border border-border bg-background-subtle px-2 py-0.5 text-[11px] text-muted-foreground"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Links */}
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
            {footerSections.map((section) => (
              <div key={section.title}>
                <h3 className="mb-3.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground-soft">
                  {section.title}
                </h3>
                <ul className="space-y-2.5">
                  {section.links.map((link) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-12 rounded-lg border border-border bg-background-subtle p-5">
          <p className="text-xs leading-relaxed text-muted-foreground text-pretty">
            <strong className="text-foreground">Дисклеймер.</strong> wr3 — это
            инструмент пред-аудита и триажа рисков. wr3 не гарантирует
            отсутствие уязвимостей, не является страховкой, не заменяет
            энтерпрайз-аудит и не выполняет эксплойты на mainnet. Результаты
            носят информационный характер и не являются публичными обвинениями.
            Человек подтверждает выводы и раскрытие. Высокий wr3-score не
            означает «secure».
          </p>
        </div>

        <div className="mt-8 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 sm:flex-row">
          <p className="text-xs text-muted-foreground-soft">
            © {new Date().getFullYear()} wr3. Пред-аудит, а не полный аудит.
          </p>
          <div className="flex gap-4">
            <a
              href="#top"
              className="text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              Конфиденциальность
            </a>
            <a
              href="#top"
              className="text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              Условия
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
