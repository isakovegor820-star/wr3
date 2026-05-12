import { Activity, Bell, FileWarning, LockKeyhole } from "lucide-react";
import { ScanConsole } from "@/components/ScanConsole";

const signals = [
  { label: "Загрузка исходников", value: "EVM-first", icon: FileWarning },
  { label: "Первый сигнал", value: "p50 цель 90с", icon: Activity },
  { label: "Приватно по умолчанию", value: "Без публичных claims", icon: LockKeyhole },
  { label: "Алерты", value: "Подписанные webhooks", icon: Bell }
];

const plans = [
  { tier: "Free", price: "$0", scans: "1 / 24ч", detail: "Предварительный score" },
  { tier: "Hobby", price: "$29", scans: "10 / месяц", detail: "Отчёты и Telegram-алерты" },
  { tier: "Team", price: "$99", scans: "100 / месяц", detail: "Foundry PoC-попытки" },
  { tier: "Pro", price: "$499", scans: "Индивидуально", detail: "Хуки мониторинга" }
];

export default function HomePage() {
  return (
    <main className="app-shell">
      <section className="workspace-band">
        <div className="workspace-copy">
          <p className="eyebrow">AI-помощник, не замена аудиту человеком</p>
          <h2>Запусти предаудит перед деплоем.</h2>
          <p>
            wr3 нормализует находки, отсекает шум, применяет прозрачный скоринг и держит
            PoC-артефакты приватными, пока владелец не подтвердил доступ.
          </p>
        </div>
        <ScanConsole />
      </section>

      <section className="signals-grid" aria-label="MVP-возможности">
        {signals.map((signal) => {
          const Icon = signal.icon;
          return (
            <article className="signal" key={signal.label}>
              <Icon aria-hidden="true" size={20} />
              <div>
                <span>{signal.label}</span>
                <strong>{signal.value}</strong>
              </div>
            </article>
          );
        })}
      </section>

      <section className="method-band">
        <div>
          <p className="eyebrow">Прозрачная методология</p>
          <h2>Пятиосевой score с hard caps для подтверждённых рисков.</h2>
        </div>
        <div className="risk-matrix" aria-label="Методология score">
          <span style={{ gridColumn: "1 / span 7" }}>Безопасность кода 35%</span>
          <span style={{ gridColumn: "8 / span 4" }}>Централизация 20%</span>
          <span style={{ gridColumn: "12 / span 3" }}>Ликвидность 15%</span>
          <span style={{ gridColumn: "15 / span 3" }}>Команда/KYC 15%</span>
          <span style={{ gridColumn: "18 / span 3" }}>On-chain поведение 15%</span>
        </div>
      </section>

      <section className="pricing-band" aria-label="Тарифы MVP">
        {plans.map((plan) => (
          <article className="pricing-card" key={plan.tier}>
            <span>{plan.tier}</span>
            <strong>{plan.price}</strong>
            <p>{plan.scans}</p>
            <p>{plan.detail}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
