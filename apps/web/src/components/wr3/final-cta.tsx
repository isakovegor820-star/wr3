import { Button } from '@/components/ui/button';
import { Logo, Wordmark } from './logo';
import { Zap, ArrowUpRight } from 'lucide-react';
import { SendIcon } from '@/components/icons/send';

export function FinalCta() {
  return (
    <section
      id="command-center"
      className="relative scroll-mt-16 overflow-hidden border-b border-border py-24 sm:py-32"
      aria-labelledby="cta-heading"
    >
      {/* Background */}
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-30" aria-hidden="true" />
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[400px] w-[700px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/10 blur-[140px]"
        aria-hidden="true"
      />

      <div className="relative mx-auto flex max-w-3xl flex-col items-center px-4 text-center sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center gap-2.5">
          <Logo size={36} />
          <Wordmark className="text-xl" />
        </div>

        <h2
          id="cta-heading"
          className="text-3xl font-semibold tracking-tight text-foreground text-balance sm:text-4xl lg:text-5xl"
        >
          Получите сигнал риска{' '}
          <span className="text-primary">до запуска</span>
        </h2>
        <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted-foreground text-pretty">
          Вставьте адрес или код — получите прозрачный wr3-score, находки с
          доказательствами и чёткий следующий шаг. Без pay-to-pass, без
          чёрных ящиков.
        </p>

        <div className="mt-8 flex w-full flex-col items-center gap-3 sm:w-auto sm:flex-row">
          <Button asChild size="lg" className="w-full gap-2 sm:w-auto">
            <a href="#top">
              <Zap className="h-4 w-4" />
              Запустить скан
            </a>
          </Button>
          <Button asChild variant="outline" size="lg" className="w-full gap-2 sm:w-auto">
            <a href="/command">
              Командный центр
              <ArrowUpRight className="h-4 w-4" />
            </a>
          </Button>
        </div>

        <a
          href="/tg"
          className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-info transition-colors hover:text-info/80"
        >
          <SendIcon className="h-4 w-4" aria-hidden="true" />
          Открыть в Telegram
        </a>

        <p className="mt-8 max-w-md text-xs leading-relaxed text-muted-foreground-soft">
          wr3 — это инструмент пред-аудита, а не полный аудит, не страховка
          и не замена энтерпрайз-аудиту. Высокий score не гарантирует
          отсутствие уязвимостей.
        </p>
      </div>
    </section>
  );
}
