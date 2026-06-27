import { cn } from '@/lib/utils';

interface LogoProps extends React.SVGProps<SVGSVGElement> {
  size?: number;
}

export function Logo({ size = 28, className, ...props }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('shrink-0', className)}
      aria-hidden="true"
      {...props}
    >
      <rect
        x="1"
        y="1"
        width="30"
        height="30"
        rx="7"
        className="fill-background"
        stroke="hsl(var(--border))"
        strokeWidth="1.5"
      />
      {/* hexagon node — represents contract analysis */}
      <path
        d="M16 6.5L23 10.25V17.75L16 21.5L9 17.75V10.25L16 6.5Z"
        className="stroke-primary"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M16 6.5L16 21.5"
        className="stroke-primary/40"
        strokeWidth="1.5"
      />
      <circle
        cx="16"
        cy="14"
        r="1.8"
        className="fill-primary animate-pulse"
        style={{ animationDuration: '3s' }}
      />
      <circle
        cx="23"
        cy="17.75"
        r="1.3"
        className="fill-success"
      />
      <circle
        cx="9"
        cy="17.75"
        r="1.3"
        className="fill-warning"
      />
      <rect
        x="3"
        y="26"
        width="6"
        height="1.5"
        rx="0.75"
        className="fill-primary/60"
      />
      <rect
        x="10.5"
        y="26"
        width="3"
        height="1.5"
        rx="0.75"
        className="fill-success/60"
      />
      <rect
        x="14.5"
        y="26"
        width="5"
        height="1.5"
        rx="0.75"
        className="fill-muted-foreground/40"
      />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn('font-semibold tracking-tight', className)}>
      wr<span className="text-primary">3</span>
    </span>
  );
}
