import { TRUST_GUARANTEES, CHAINS } from './data';
import { cn } from '@/lib/utils';
import {
  Lock,
  ShieldCheck,
  Ban,
  Eye,
  type LucideIcon,
} from 'lucide-react';

const iconMap: Record<string, LucideIcon> = {
  lock: Lock,
  shield: ShieldCheck,
  ban: Ban,
  eye: Eye,
};

export function TrustBar() {
  return (
    <section
      className="relative border-b border-border bg-background-subtle py-10"
      aria-labelledby="trust-heading"
    >
      <h2 id="trust-heading" className="sr-only">
        Поддерживаемые сети и гарантии
      </h2>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground-soft">
            Поддерживаемые сети
          </span>
          {CHAINS.map((c) => (
            <span
              key={c.value}
              className="mono text-sm font-medium text-muted-foreground"
            >
              {c.short}
            </span>
          ))}
        </div>

        <div
          className="grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-4"
          role="list"
        >
          {TRUST_GUARANTEES.map((g) => {
            const Icon = iconMap[g.icon];
            return (
              <div
                key={g.title}
                role="listitem"
                className="group flex flex-col gap-2 bg-background-subtle p-5 transition-colors hover:bg-card"
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-background text-primary">
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <h3 className="text-sm font-semibold text-foreground">
                    {g.title}
                  </h3>
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {g.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export { Lock, ShieldCheck, Ban, Eye, cn };
