import { SectionHeading } from './section';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Radar, ArrowRight, Bot, Check, Clock, Layers, Bell, Database } from 'lucide-react';

const scoutFlow = [
  {
    icon: Database,
    title: 'Находит протоколы',
    description: 'Мониторит DeFiLlama и сетевую активность. Не требует вашего участия.',
  },
  {
    icon: ArrowRight,
    title: 'Ставит пред-аудиты в очередь',
    description: 'Автоматически запускает скан conвейера по найденным целям.',
  },
  {
    icon: Layers,
    title: 'Дедуплицирует цели',
    description: 'Отслеживает уже проверенные адреса и обновления bytecode.',
  },
  {
    icon: Clock,
    title: 'Формирует очередь ревью',
    description: 'Приоритизирует находки по severity. Человек только подтверждает.',
  },
];

export function ScoutSection() {
  return (
    <section
      id="scout"
      className="relative scroll-mt-16 border-b border-border py-20 sm:py-28"
      aria-labelledby="scout-heading"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-[1fr_1.1fr] lg:gap-16">
          {/* Left: Scout explainer */}
          <div>
            <SectionHeading
              tag="Автоматизация"
              title={<>Scout-автопилот <span className="text-primary">24/7</span></>}
              description="Scout самостоятельно находит новые протоколы, ставит пред-аудиты в очередь, дедуплицирует цели и формирует очередь на ревью. Вам остаётся подтвердить выводы."
              className="mb-10"
            />

            <ol className="space-y-3" aria-label="Цикл работы Scout">
              {scoutFlow.map((s, i) => {
                const Icon = s.icon;
                return (
                  <li
                    key={s.title}
                    className="flex items-start gap-3.5"
                  >
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-background-subtle text-primary">
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">
                        <span className="mono mr-1.5 text-muted-foreground-soft">
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        {s.title}
                      </h3>
                      <p className="mt-0.5 text-sm text-muted-foreground text-pretty">
                        {s.description}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>

            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild className="gap-2">
                <a href="/command">
                  <Radar className="h-4 w-4" />
                  Включить Scout
                </a>
              </Button>
              <Button asChild variant="outline" className="gap-2">
                <a href="/command">
                  Командный центр
                  <ArrowRight className="h-4 w-4" />
                </a>
              </Button>
            </div>
          </div>

          {/* Right: Scout dashboard mockup + Telegram delivery */}
          <div className="flex flex-col gap-6">
            {/* Dashboard mock */}
            <Card className="relative overflow-hidden border-border bg-card-elevated p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Radar className="h-4 w-4 text-primary" aria-hidden="true" />
                  <span className="text-sm font-medium">Scout · очередь ревью</span>
                </div>
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
                  </span>
                  live
                </span>
              </div>

              <div className="space-y-2.5">
                {[
                  { name: 'VaultX v2', chain: 'ARB', sev: 'High', score: 42 },
                  { name: 'StableSwap-Mini', chain: 'BASE', sev: 'Medium', score: 61 },
                  { name: 'LendProtocol / LST', chain: 'ETH', sev: 'Low', score: 78 },
                ].map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center gap-3 rounded-lg border border-border bg-background-subtle p-3 text-sm"
                  >
                    <span className="mono text-xs font-medium text-muted-foreground">
                      {item.chain}
                    </span>
                    <span className="flex-1 truncate font-medium text-foreground">
                      {item.name}
                    </span>
                    <span
                      className={cn(
                        'mono text-xs font-bold',
                        item.score >= 75
                          ? 'text-success'
                          : item.score >= 50
                            ? 'text-warning'
                            : 'text-destructive'
                      )}
                    >
                      {item.score}
                    </span>
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold',
                        item.sev === 'High' &&
                          'bg-destructive/12 text-destructive',
                        item.sev === 'Medium' &&
                          'bg-warning/12 text-warning',
                        item.sev === 'Low' &&
                          'bg-info/12 text-info'
                      )}
                    >
                      {item.sev}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <Check className="h-3.5 w-3.5 text-success" aria-hidden="true" />
                  127 протоколов в очереди · 42 в ревью
                </span>
                <span className="mono">обновлено 12с назад</span>
              </div>
            </Card>

            {/* Telegram delivery */}
            <Card className="relative overflow-hidden border-border bg-card p-5">
              <div className="mb-4 flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-info/10 text-info">
                  <Bot className="h-4 w-4" aria-hidden="true" />
                </span>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">
                    Telegram-доставка
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    wr3-бот и мини-апп
                  </p>
                </div>
                <Badge variant="outline" className="ml-auto border-info/30 text-info">
                  <Bell className="mr-1 h-3 w-3" aria-hidden="true" />
                  Алерты
                </Badge>
              </div>

              {/* Mock Telegram message */}
              <div className="space-y-3">
                <div className="rounded-lg rounded-bl-sm border border-border bg-background-subtle p-3">
                  <div className="mb-1.5 flex items-center justify-between">
                    <span className="mono text-xs font-medium text-info">wr3_bot</span>
                    <span className="text-[10px] text-muted-foreground-soft">14:32</span>
                  </div>
                  <p className="text-sm font-medium text-foreground">
                    Новый пред-аудит готов
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    VaultX v2 · Arbitrum · wr3-score <span className="font-semibold text-warning">42</span>
                  </p>
                  <div className="mt-2 flex gap-1.5">
                    <span className="rounded bg-destructive/12 px-1.5 py-0.5 text-[10px] font-semibold text-destructive">
                      2 High
                    </span>
                    <span className="rounded bg-warning/12 px-1.5 py-0.5 text-[10px] font-semibold text-warning">
                      3 Medium
                    </span>
                    <span className="rounded bg-info/12 px-1.5 py-0.5 text-[10px] font-semibold text-info">
                      4 Low
                    </span>
                  </div>
                </div>
                <p className="flex items-center gap-1.5 text-xs text-muted-foreground-soft">
                  <Check className="h-3 w-3 text-success" aria-hidden="true" />
                  Человек подтверждает выводы и раскрытие. Рутину делает платформа.
                </p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}
