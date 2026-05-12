"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { AuditState } from "@wr3/shared";

const terminalStates: AuditState[] = ["completed", "failed", "needs_source", "partial", "rejected", "terminal"];

export function StatusRefresher({ state }: { state: AuditState }) {
  const router = useRouter();

  useEffect(() => {
    if (terminalStates.includes(state)) {
      return;
    }
    const timer = window.setTimeout(() => router.refresh(), 1800);
    return () => window.clearTimeout(timer);
  }, [router, state]);

  return null;
}
