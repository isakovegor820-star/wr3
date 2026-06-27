import { AlertTriangle, ShieldAlert, ShieldCheck, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

const config: Record<
  Severity,
  {
    label: string;
    icon: React.ElementType;
    className: string;
  }
> = {
  critical: {
    label: 'Critical',
    icon: ShieldAlert,
    className:
      'border-destructive/30 bg-destructive/12 text-destructive [&_svg]:text-destructive',
  },
  high: {
    label: 'High',
    icon: AlertTriangle,
    className:
      'border-warning/30 bg-warning/12 text-warning [&_svg]:text-warning',
  },
  medium: {
    label: 'Medium',
    icon: AlertTriangle,
    className:
      'border-warning/20 bg-warning/8 text-warning [&_svg]:text-warning',
  },
  low: {
    label: 'Low',
    icon: Info,
    className:
      'border-info/25 bg-info/10 text-info [&_svg]:text-info',
  },
  info: {
    label: 'Info',
    icon: Info,
    className:
      'border-muted-foreground/25 bg-muted text-muted-foreground [&_svg]:text-muted-foreground',
  },
};

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity;
  className?: string;
}) {
  const cfg = config[severity];
  const Icon = cfg.icon;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold',
        cfg.className,
        className
      )}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

export function ScoreRing({
  score,
  size = 56,
}: {
  score: number;
  size?: number;
}) {
  const clamped = Math.max(0, Math.min(100, score));
  const radius = (size - 6) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  const ringColor =
    clamped >= 75
      ? 'stroke-success'
      : clamped >= 50
        ? 'stroke-warning'
        : 'stroke-destructive';
  const label = clamped >= 75 ? 'Низкий риск' : clamped >= 50 ? 'Средний риск' : 'Высокий риск';

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`wr3-score ${clamped} из 100 — ${label}`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth="3"
          className="stroke-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={cn('transition-all duration-700 ease-out-expo', ringColor)}
        />
      </svg>
      <div className="absolute flex flex-col items-center leading-none">
        <span className="mono text-sm font-bold">{clamped}</span>
        <IconShield className="mt-0.5 h-2.5 w-2.5 text-muted-foreground" />
      </div>
    </div>
  );
}

function IconShield({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 2L4 5v6c0 5 3.4 9.5 8 11 4.6-1.5 8-6 8-11V5l-8-3z" />
    </svg>
  );
}

export { ShieldCheck };
