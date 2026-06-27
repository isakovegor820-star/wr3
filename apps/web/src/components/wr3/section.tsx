import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

export function SectionTag({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full border border-border bg-background-subtle px-3 py-1 text-xs font-medium uppercase tracking-wider text-muted-foreground',
        className
      )}
    >
      {children}
    </span>
  );
}

export function SectionHeading({
  tag,
  title,
  description,
  align = 'left',
  className,
}: {
  tag?: string;
  title: ReactNode;
  description?: ReactNode;
  align?: 'left' | 'center';
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4',
        align === 'center' &&
          'mx-auto max-w-2xl items-center text-center',
        className
      )}
    >
      {tag && <SectionTag>{tag}</SectionTag>}
      <h2 className="text-3xl font-semibold tracking-tight text-foreground text-balance sm:text-4xl">
        {title}
      </h2>
      {description && (
        <p className="max-w-2xl text-base leading-relaxed text-muted-foreground text-pretty">
          {description}
        </p>
      )}
    </div>
  );
}
