"use client";

import { useEffect, useState } from "react";
import { CreditCard, ShieldCheck } from "lucide-react";
import type { Tier } from "@wr3/shared";
import { getBillingPlans, getLocalSubscription, type BillingPlan } from "@/lib/api";
import { tierLabels } from "@/lib/i18n";

const tiers: Tier[] = ["free", "hobby", "team", "pro"];

export function BillingMock() {
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [tier, setTier] = useState<Tier>("free");
  const [subscription, setSubscription] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedTier = window.localStorage.getItem("wr3-local-tier") as Tier | null;
    if (storedTier && tiers.includes(storedTier)) {
      setTier(storedTier);
    }
    void Promise.all([getBillingPlans(), getLocalSubscription()])
      .then(([nextPlans, nextSubscription]) => {
        setPlans(nextPlans);
        setSubscription(nextSubscription);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Симулятор тарифов не загрузился"));
  }, []);

  function chooseTier(nextTier: Tier) {
    setTier(nextTier);
    window.localStorage.setItem("wr3-local-tier", nextTier);
  }

  return (
    <section className="panel billing-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Локальный биллинг</p>
          <h2>Симулятор тарифа и квоты для localhost</h2>
        </div>
        <div className="safe-harbor-signal">
          <ShieldCheck aria-hidden="true" size={18} />
          <span>Тариф проверяется на стороне API</span>
        </div>
      </div>

      {error ? <p className="error-box">{error}</p> : null}

      <div className="billing-current">
        <CreditCard aria-hidden="true" size={22} />
        <div>
          <span>Текущий локальный тариф</span>
          <strong>{tierLabels[tier]}</strong>
        </div>
      </div>

      <div className="pricing-band local-pricing">
        {plans.map((plan) => (
          <article className={`pricing-card ${tier === plan.tier ? "selected-card" : ""}`} key={plan.tier}>
            <span>{tierLabels[plan.tier]}</span>
            <strong>${plan.price_usd_month}</strong>
            <p>{plan.scan_quota}</p>
            <p>{plan.poc_access ? "Локальный PoC доступен" : "PoC закрыт или работает в ограниченном режиме"}</p>
            <button type="button" className="secondary-button" onClick={() => chooseTier(plan.tier)}>
              Выбрать локально
            </button>
          </article>
        ))}
      </div>

      <div className="raw-gated">
        <CreditCard aria-hidden="true" size={22} />
        <div>
          <h2>Как это влияет на скан</h2>
          <p>
            Консоль скана читает локальный тариф из браузера и отправляет его в API. Квота и ограниченный режим
            проверяются на стороне backend, поэтому переключатель в интерфейсе не заменяет реальный биллинг в production.
          </p>
          <pre className="json-preview">{JSON.stringify(subscription, null, 2)}</pre>
        </div>
      </div>
    </section>
  );
}
