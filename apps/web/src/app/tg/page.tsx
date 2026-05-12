import { Bell, ExternalLink, Radar } from "lucide-react";
import Link from "next/link";
import { ScanConsole } from "@/components/ScanConsole";

const actions = [
  { label: "/scan", value: "предварительный score", icon: Radar },
  { label: "/watch", value: "очередь алертов", icon: Bell },
  { label: "Web-отчёт", value: "детали только для owner", icon: ExternalLink }
];

export default function TelegramMiniAppPage() {
  return (
    <main className="app-shell mini-shell">
      <nav className="top-nav">
        <Link href="/">Открыть веб-версию</Link>
      </nav>

      <section className="mini-grid">
        <ScanConsole />
        <div className="signals-grid mini-signals" aria-label="Telegram-действия">
          {actions.map((action) => {
            const Icon = action.icon;
            return (
              <article className="signal" key={action.label}>
                <Icon aria-hidden="true" size={20} />
                <div>
                  <span>{action.label}</span>
                  <strong>{action.value}</strong>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
