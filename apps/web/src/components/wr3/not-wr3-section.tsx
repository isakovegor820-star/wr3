'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { NOT_WR3 } from './data';
import { SectionHeading } from './section';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CHAINS } from './data';
import { AlertOctagon, Search, ArrowRight, type LucideIcon } from 'lucide-react';

const X = AlertOctagon;

export function NotWr3Section() {
  return (
    <section
      id="verify-address"
      className="relative scroll-mt-16 border-b border-border bg-background-subtle py-20 sm:py-28"
      aria-labelledby="not-wr3-heading"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          tag="Честные границы"
          title="Чем wr3 не является"
          description="Доверие через прозрачность. wr3 — это сигнал риска пред-аудита, а не полный аудит и не страховка. Таких вещей мы не делаем."
          align="center"
          className="mb-14"
        />

        <div className="mb-16 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {NOT_WR3.map((item) => (
            <Card
              key={item.title}
              className="border-border bg-card p-5"
            >
              <div className="mb-3 flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-background text-destructive">
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                <h3 className="text-sm font-semibold text-foreground">
                  {item.title}
                </h3>
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground text-pretty">
                {item.description}
              </p>
            </Card>
          ))}
        </div>

        {/* Public address verification */}
        <PublicVerification />
      </div>
    </section>
  );
}

const PUBLIC_CHAIN_MAP: Record<string, string> = {
  eth: 'ethereum',
  base: 'base',
  bsc: 'bsc',
  arb: 'arbitrum',
  sol: 'solana',
};

function PublicVerification() {
  const router = useRouter();
  const [chain, setChain] = useState('eth');
  const [addr, setAddr] = useState('');

  const open = () => {
    const value = addr.trim();
    if (!value) return;
    router.push(`/p/${PUBLIC_CHAIN_MAP[chain] ?? 'ethereum'}/${encodeURIComponent(value)}`);
  };

  return (
    <Card
      id="public-verify"
      className="relative overflow-hidden border-border bg-card p-6 sm:p-8"
    >
      <div
        className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/[0.05] to-transparent"
        aria-hidden="true"
      />
      <div className="relative grid gap-8 lg:grid-cols-[1fr_1.2fr] lg:items-center">
        <div>
          <h3 className="mb-3 text-2xl font-semibold tracking-tight text-foreground text-balance">
            Публичная проверка по адресу
          </h3>
          <p className="mb-5 text-base leading-relaxed text-muted-foreground text-pretty">
            Проверьте любой публичный контракт по адресу. Карточка проекта
            содержит wr3-score, находки с провенансом и список того, что ещё
            не покрыто. Без регистрации.
          </p>
          <ul className="space-y-2.5 text-sm text-muted-foreground">
            {[
              'Карточка проекта по адресу контракта',
              'Сводка находок и покрытые/непокрытые категории',
              'Провенанс каждой находки до источника',
            ].map((item) => (
              <li key={item} className="flex items-start gap-2">
                <Search className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-border bg-background-subtle p-4 sm:p-5">
          <label
            htmlFor="verify-input"
            className="mb-2 block text-xs font-medium text-muted-foreground"
          >
            Адрес контракта
          </label>
          <div className="flex gap-2">
            <Select value={chain} onValueChange={setChain}>
              <SelectTrigger className="w-[110px] shrink-0" aria-label="Сеть">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHAINS.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.short}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              id="verify-input"
              type="text"
              placeholder="0x7a3F…c2e1"
              className="flex-1 font-mono text-sm"
              value={addr}
              onChange={(e) => setAddr(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') open();
              }}
            />
          </div>
          <Button className="mt-3 w-full gap-2" size="lg" onClick={open} disabled={!addr.trim()}>
            <Search className="h-4 w-4" />
            Проверить публично
          </Button>
          <p className="mt-3 text-center text-[11px] text-muted-foreground-soft">
            Публичная карточка содержит только результаты публично доступных
            адресов.
          </p>
        </div>
      </div>
    </Card>
  );
}

export type { LucideIcon };
