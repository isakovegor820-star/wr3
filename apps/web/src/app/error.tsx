"use client";

import Link from "next/link";
import { AlertTriangle } from "lucide-react";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="app-shell">
      <div className="panel" style={{ display: "grid", gap: 14, margin: "64px auto", maxWidth: 560, padding: 28 }}>
        <div className="audit-load-error">
          <AlertTriangle aria-hidden="true" size={22} />
          <div>
            <p className="eyebrow">Что-то пошло не так</p>
            <h1 style={{ fontSize: 24, margin: "4px 0 0" }}>Не удалось загрузить страницу</h1>
          </div>
        </div>
        <p style={{ color: "var(--muted)", lineHeight: 1.55, margin: 0 }}>
          Возможно, API недоступен или данные не найдены. Проверьте, что бэкенд запущен
          (http://127.0.0.1:8001), и попробуйте снова.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          <button type="button" onClick={reset}>
            Повторить
          </button>
          <Link href="/" className="secondary-button" style={{ alignItems: "center", borderRadius: 8, display: "inline-flex", minHeight: 42, padding: "0 14px" }}>
            На главную
          </Link>
        </div>
      </div>
    </main>
  );
}
