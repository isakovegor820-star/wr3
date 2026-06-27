'use client';

import { useState, useEffect } from 'react';
import { Logo, Wordmark } from './logo';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Menu, X, ArrowUpRight } from 'lucide-react';

const navLinks = [
  { href: '#what-inside', label: 'Что внутри' },
  { href: '#how-it-works', label: 'Как работает' },
  { href: '#scout', label: 'Scout' },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={cn(
        'fixed inset-x-0 top-0 z-50 transition-colors duration-300',
        scrolled
          ? 'border-b border-border/70 bg-background/80 backdrop-blur-lg supports-[backdrop-filter]:bg-background/60'
          : 'border-b border-transparent bg-transparent'
      )}
    >
      <nav
        className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8"
        aria-label="Основная навигация"
      >
        <a
          href="#top"
          className="flex items-center gap-2.5 text-lg"
          aria-label="wr3 — главная"
        >
          <Logo size={32} />
          <Wordmark className="text-xl" />
        </a>

        <div className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </div>

        <div className="hidden items-center gap-3 md:flex">
          <Button asChild variant="ghost" size="sm">
            <a href="#top" className="text-muted-foreground">
              Проверить адрес
            </a>
          </Button>
          <Button asChild size="sm" className="gap-1.5">
            <a href="/command">
              Командный центр
              <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
          </Button>
        </div>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring md:hidden"
          aria-label={open ? 'Закрыть меню' : 'Открыть меню'}
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>

      {/* Mobile menu */}
      {open && (
        <div
          id="mobile-nav"
          className="border-t border-border bg-background/95 backdrop-blur-lg md:hidden"
        >
          <div className="space-y-1 px-4 py-4">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="block rounded-md px-3 py-2.5 text-base font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
            <div className="flex flex-col gap-3 pt-3">
              <Button asChild variant="outline" size="sm">
                <a href="#top" onClick={() => setOpen(false)}>
                  Проверить адрес
                </a>
              </Button>
              <Button asChild size="sm">
                <a href="/command" onClick={() => setOpen(false)}>
                  Командный центр
                </a>
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
