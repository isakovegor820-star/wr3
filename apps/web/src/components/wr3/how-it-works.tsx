import { PIPELINE_STEPS } from './data';
import { SectionHeading } from './section';
import { cn } from '@/lib/utils';
import {
  Download,
  Search,
  Cpu,
  FlaskConical,
  Gauge,
  FileCheck2,
  type LucideIcon,
} from 'lucide-react';

const iconMap: Record<string, LucideIcon> = {
  download: Download,
  search: Search,
  cpu: Cpu,
  'flask-conical': FlaskConical,
  gauge: Gauge,
  'file-check': FileCheck2,
};

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="relative scroll-mt-16 border-b border-border bg-background-subtle py-20 sm:py-28"
      aria-labelledby="how-heading"
    >
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-20" aria-hidden="true" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          tag="Как работает"
          title="Сквозной конвейер аудита"
          description="Шесть этапов работают автоматически. Вы не настраиваете инструменты и не собираете результаты вручную — платформа делает это сама."
          className="mb-14"
        />

        <ol
          className="relative grid gap-4 lg:grid-cols-3"
          aria-label="Этапы конвейера аудита"
        >
          {PIPELINE_STEPS.map((step, i) => {
            const Icon = iconMap[step.icon];
            const stepNum = i + 1;
            return (
              <li
                key={step.id}
                className="group relative flex flex-col rounded-xl border border-border bg-card p-6 transition-colors hover:bg-card-elevated"
              >
                <div className="mb-4 flex items-center justify-between">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <span
                    className="mono text-3xl font-bold text-border/60 transition-colors group-hover:text-primary/30"
                    aria-hidden="true"
                  >
                    {String(stepNum).padStart(2, '0')}
                  </span>
                </div>
                <h3 className="mb-2 text-base font-semibold text-foreground">
                  {step.title}
                </h3>
                <p className="mb-4 flex-1 text-sm leading-relaxed text-muted-foreground text-pretty">
                  {step.description}
                </p>
                <p className="border-t border-border pt-3 font-mono text-xs text-muted-foreground-soft">
                  {step.tools}
                </p>

                {/* Connector arrow on large screens */}
                {stepNum < PIPELINE_STEPS.length && (
                  <span
                    className="pointer-events-none absolute -right-2 top-1/2 hidden -translate-y-1/2 text-border lg:block"
                    aria-hidden="true"
                  >
                    <svg
                      className={cn(stepNum % 3 === 0 && 'hidden')}
                      width="16"
                      height="16"
                      viewBox="0 0 16 16"
                      fill="none"
                    >
                      <path
                        d="M6 4l4 4-4 4"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                )}

                {/* Visual step indicator */}
                <span
                  className="absolute left-0 top-6 h-[calc(100%-3rem)] w-px bg-gradient-to-b from-primary/40 to-transparent"
                  aria-hidden="true"
                  style={{ display: i < PIPELINE_STEPS.length - 1 ? 'block' : 'none' }}
                />
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
