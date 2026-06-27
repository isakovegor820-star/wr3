import { WHAT_YOU_GET } from './data';
import { SectionHeading } from './section';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import {
  Gauge,
  FileSearch,
  ShieldCheck,
  Zap,
  Compass,
  Megaphone,
  type LucideIcon,
} from 'lucide-react';

const iconMap: Record<string, LucideIcon> = {
  gauge: Gauge,
  'file-search': FileSearch,
  shield: ShieldCheck,
  zap: Zap,
  compass: Compass,
  megaphone: Megaphone,
};

const accentMap: Record<string, string> = {
  primary: 'text-primary [&_.icon-box]:border-primary/30 [&_.icon-box]:bg-primary/10',
  success: 'text-success [&_.icon-box]:border-success/30 [&_.icon-box]:bg-success/10',
  warning: 'text-warning [&_.icon-box]:border-warning/30 [&_.icon-box]:bg-warning/10',
  info: 'text-info [&_.icon-box]:border-info/30 [&_.icon-box]:bg-info/10',
};

export function WhatYouGet() {
  return (
    <section
      id="what-inside"
      className="relative scroll-mt-16 border-b border-border py-20 sm:py-28"
      aria-labelledby="what-you-get-heading"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          tag="Что вы получаете"
          title="Удобство и качество. Без компромиссов."
          description="wr3 спроектирован для тревожных билдеров: быстро снимает неопределённость, не прячет оговорки и ведёт к следующему безопасному шагу."
          className="mb-12"
        />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {WHAT_YOU_GET.map((item) => {
            const Icon = iconMap[item.icon];
            return (
              <Card
                key={item.id}
                className={cn(
                  'group relative overflow-hidden border-border bg-card p-6 transition-colors hover:border-border/80 hover:bg-card-elevated',
                  accentMap[item.accent]
                )}
              >
                <div className="mb-4 flex items-center justify-between">
                  <span className="icon-box flex h-11 w-11 items-center justify-center rounded-lg border">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <span className="rounded-full border border-border bg-background-subtle px-2 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    {item.tag}
                  </span>
                </div>
                <h3 className="mb-2 text-base font-semibold text-foreground">
                  {item.title}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground text-pretty">
                  {item.description}
                </p>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
