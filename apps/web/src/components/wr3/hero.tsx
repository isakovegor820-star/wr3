'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createAudit } from '@/lib/api';
import type { Chain } from '@wr3/shared';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Logo, Wordmark } from './logo';
import { SeverityBadge, ScoreRing } from './severity';
import {
  TARGET_PLACEHOLDER,
  SCAN_DEPTH_OPTIONS,
  type ChainOption,
  CHAINS,
} from './data';
import { cn } from '@/lib/utils';
import { Zap, ArrowRight, ShieldCheck, Lock, Loader2, AlertTriangle } from 'lucide-react';

type ScanState = 'idle' | 'scanning' | 'preview';

const CHAIN_MAP: Record<ChainOption['value'], Chain> = {
  eth: 'ethereum',
  base: 'base',
  bsc: 'bsc',
  arb: 'arbitrum',
  sol: 'solana',
};

const DEPTH_MAP: Record<string, 'preliminary' | 'standard' | 'deep'> = {
  fast: 'preliminary',
  deep: 'deep',
};

export function Hero() {
  const router = useRouter();
  const [chain, setChain] = useState<ChainOption['value']>('eth');
  const [depth, setDepth] = useState<string>('fast');
  const [target, setTarget] = useState('');
  const [state, setState] = useState<ScanState>('idle');
  const [error, setError] = useState<string | null>(null);

  const canScan = target.trim().length >= 10;

  const handleScan = async () => {
    if (!canScan || state === 'scanning') return;
    setError(null);
    setState('scanning');
    const raw = target.trim();
    const isAddress = /^0x[a-fA-F0-9]{40}$/.test(raw);
    try {
      const res = await createAudit({
        chain: CHAIN_MAP[chain],
        address: isAddress ? raw : '',
        source: isAddress ? '' : raw,
        allow_bytecode_only: isAddress,
        requested_depth: DEPTH_MAP[depth] ?? 'preliminary',
        visibility: 'private',
        user_intent: 'pre_launch_self_check',
      });
      router.push(
        `/audits/${res.audit_id}?owner_token=${encodeURIComponent(res.owner_access_token)}`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Скан не запустился');
      setState('idle');
    }
  };

  return (
    <section
      id="top"
      className="relative overflow-hidden border-b border-border"
      aria-labelledby="hero-heading"
    >
      {/* Background layers */}
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-40" aria-hidden="true" />
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-[520px] bg-gradient-to-b from-primary/[0.07] via-transparent to-transparent"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-[400px] w-[800px] -translate-x-1/2 rounded-full bg-primary/10 blur-[120px] opacity-50"
        aria-hidden="true"
      />

      <div className="relative mx-auto max-w-7xl px-4 pb-16 pt-28 sm:px-6 sm:pt-32 lg:px-8 lg:pb-20 lg:pt-40">
        <div className="grid gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10">
          {/* Left: headline + offser */}
          <div className="flex flex-col justify-center">
            <div className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-border bg-background-subtle px-3 py-1.5 text-xs font-medium text-muted-foreground">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
              </span>
              Пред-аудит, а не «сканер-казино». Safety-first.
            </div>

            <h1
              id="hero-heading"
              className="text-4xl font-semibold leading-[1.05] tracking-tight text-foreground text-balance sm:text-5xl lg:text-6xl"
            >
              Сигнал риска{' '}
              <span className="text-primary">до запуска контракта</span>,{' '}
              а не после
            </h1>

            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted-foreground text-pretty">
              wr3 — AI-ассистированный пред-аудит и триаж смарт-контрактов. Не
              заменяет полный аудит, а даёт быстрый, прозрачный и доказательный
              сигнал. Вставьте адрес или код — получите результат за минуты.
            </p>

            <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
              {[
                'Локально и приватно',
                'ZDR-маршрут для LLM-триажа',
                'Без передачи находок',
              ].map((item) => (
                <li key={item} className="flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-success" aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>

            {/* Pills of supported chains */}
            <div className="mt-8">
              <p className="mb-2.5 text-xs font-medium uppercase tracking-wider text-muted-foreground-soft">
                Ethereum · Base · BSC · Arbitrum · Solana (beta)
              </p>
            </div>
          </div>

          {/* Right: scan form / live preview */}
          <div className="relative flex items-center justify-center lg:justify-end">
            <ScanPanel
              chain={chain}
              setChain={setChain}
              depth={depth}
              setDepth={setDepth}
              target={target}
              setTarget={setTarget}
              state={state}
              setState={setState}
              canScan={canScan}
              onScan={handleScan}
              error={error}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function ScanPanel({
  chain,
  setChain,
  depth,
  setDepth,
  target,
  setTarget,
  state,
  setState,
  canScan,
  onScan,
  error,
}: {
  chain: string;
  setChain: (v: ChainOption['value']) => void;
  depth: string;
  setDepth: (v: string) => void;
  target: string;
  setTarget: (v: string) => void;
  state: ScanState;
  setState: (s: ScanState) => void;
  canScan: boolean;
  onScan: () => void | Promise<void>;
  error: string | null;
}) {
  const selectedChain = CHAINS.find((c) => c.value === chain);

  return (
    <div className="panel-border relative w-full max-w-md overflow-hidden rounded-2xl bg-card/80 backdrop-blur-sm">
      {/* Panel header — like terminal/tab */}
      <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-destructive/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-warning/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-success/60" />
          <span className="ml-2 font-mono text-xs text-muted-foreground">
            wr3-scan
          </span>
        </div>
        <span className="font-mono text-[11px] text-muted-foreground-soft">
          v0.9 beta
        </span>
      </div>

      <div className="p-5">
        {state === 'idle' && (
          <div className="animate-fade-in space-y-4">
            <div className="flex items-center gap-2.5">
              <Logo size={20} />
              <Wordmark className="text-sm" />
              <span className="ml-auto text-xs text-muted-foreground">
                Быстрый скан
              </span>
            </div>

            {/* Chain selector + target input */}
            <div className="space-y-2">
              <label
                htmlFor="scan-target"
                className="text-xs font-medium text-muted-foreground"
              >
                Адрес контракта или исходный код
              </label>
              <div className="flex gap-2">
                <Select value={chain} onValueChange={(v) => setChain(v as ChainOption['value'])}>
                  <SelectTrigger className="w-[110px] shrink-0" aria-label="Сеть">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CHAINS.map((c) => (
                      <SelectItem key={c.value} value={c.value}>
                        {c.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  id="scan-target"
                  type="text"
                  placeholder={TARGET_PLACEHOLDER}
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  className="flex-1 font-mono text-sm"
                  aria-describedby="scan-hint"
                />
              </div>
            </div>

            {/* Depth selector */}
            <div className="space-y-2">
              <span className="text-xs font-medium text-muted-foreground">
                Глубина
              </span>
              <div className="grid grid-cols-2 gap-2">
                {SCAN_DEPTH_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setDepth(opt.value)}
                    aria-pressed={depth === opt.value}
                    className={cn(
                      'flex items-center justify-between rounded-lg border px-3 py-2.5 text-left text-sm transition-colors',
                      depth === opt.value
                        ? 'border-primary/50 bg-primary/10 text-foreground'
                        : 'border-border bg-background-subtle text-muted-foreground hover:border-border hover:text-foreground'
                    )}
                  >
                    <span className="flex flex-col gap-0.5">
                      <span className="font-medium">{opt.label}</span>
                      <span className="text-[11px] text-muted-foreground-soft">
                        {opt.time}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-2.5 pt-1">
              <Button
                onClick={onScan}
                disabled={!canScan}
                className="w-full gap-2"
                size="lg"
              >
                <Zap className="h-4 w-4" />
                Запустить скан
              </Button>
              <Button asChild variant="outline" className="w-full gap-2" size="lg">
                <a href="/command">
                  Командный центр
                  <ArrowRight className="h-4 w-4" />
                </a>
              </Button>
            </div>

            {error && (
              <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {error}
              </p>
            )}

            <p
              id="scan-hint"
              className="flex items-center gap-1.5 pt-1 text-[11px] text-muted-foreground-soft"
            >
              <Lock className="h-3 w-3" aria-hidden="true" />
              Приватно. PoC/фаззинг только в песочнице — без mainnet и --ffi.
            </p>
          </div>
        )}

        {state === 'scanning' && <ScanningState chain={selectedChain?.label ?? ''} />}

        {state === 'preview' && (
          <PreviewState chain={selectedChain?.label ?? ''} onReset={() => setState('idle')} /> 
        )}
      </div>
    </div>
  );
}

function ScanningState({ chain }: { chain: string }) {
  const steps = [
    'Ингест и нормализация',
    'Slither → Aderyn → Wake',
    'Мульти-агентный LLM-триаж',
    'PoC / фаззинг в песочнице',
    'Скоринг wr3-score',
  ];
  return (
    <div className="animate-fade-in space-y-4 py-2" role="status" aria-live="polite">
      <div className="flex items-center gap-2.5">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        <span className="text-sm font-medium">Анализ на {chain}…</span>
      </div>
      <div className="space-y-2.5">
        {steps.map((step, i) => (
          <div
            key={step}
            className="flex items-center gap-2.5"
            style={{ opacity: i < 3 ? 1 : 0.4 }}
          >
            <div
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                i < 3 ? 'bg-primary' : 'bg-muted-foreground/40'
              )}
            />
            <span className="font-mono text-xs text-muted-foreground">
              {step}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PreviewState({ chain, onReset }: { chain: string; onReset: () => void }) {
  return (
    <div className="animate-fade-in space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground">Результат скана</p>
          <p className="mono truncate text-sm font-medium">
            0x7a3F…c2e1 · {chain}
          </p>
        </div>
        <ScoreRing score={68} size={52} />
      </div>

      <div className="space-y-2 rounded-lg border border-border bg-background-subtle p-3">
        <p className="text-xs font-medium text-muted-foreground">
          Найдено находок
        </p>
        {[
          { sev: 'high' as const, title: 'Unchecked callback return value', src: 'Slither' },
          { sev: 'medium' as const, title: 'Missing zero-address check', src: 'Aderyn' },
          { sev: 'low' as const, title: 'Event not emitted on state change', src: 'Wake' },
        ].map((f) => (
          <div
            key={f.title}
            className="flex items-center justify-between gap-2 text-xs"
          >
            <span className="flex items-center gap-2 truncate">
              <SeverityBadge severity={f.sev} />
              <span className="truncate text-muted-foreground">{f.title}</span>
            </span>
            <span className="shrink-0 font-mono text-muted-foreground-soft">
              {f.src}
            </span>
          </div>
        ))}
      </div>

      <div className="flex items-start gap-2 rounded-lg border border-warning/20 bg-warning/[0.06] p-3 text-xs text-muted-foreground">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" aria-hidden="true" />
        <span>
          Это <strong className="text-foreground">пред-аудит</strong>, не
          полный аудит. 6 категорий не покрыто (upgradability,
          cross-contract бизнес-логика). Не запускать без ревью.
        </span>
      </div>

      <Button variant="outline" className="w-full gap-2" onClick={onReset}>
        Новый скан
        <ArrowRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
