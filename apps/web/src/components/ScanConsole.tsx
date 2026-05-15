"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, ClipboardPaste, Cpu, Loader2, ShieldAlert } from "lucide-react";
import type { Chain, Tier } from "@wr3/shared";
import { createAudit } from "@/lib/api";

const sampleSource = `contract Vault {
    address public owner;

    function auth(address expected) public view {
        require(tx.origin == expected, "bad auth");
    }
}`;

const chains: { value: Chain; label: string; note?: string }[] = [
  { value: "base", label: "Base" },
  { value: "ethereum", label: "ETH" },
  { value: "bsc", label: "BSC" },
  { value: "arbitrum", label: "ARB" },
  { value: "solana", label: "Solana", note: "beta" }
];

const depths: { value: "preliminary" | "standard" | "deep"; label: string }[] = [
  { value: "preliminary", label: "Быстро" },
  { value: "standard", label: "Стандарт" },
  { value: "deep", label: "Глубоко" }
];

export function ScanConsole() {
  const router = useRouter();
  const [chain, setChain] = useState<Chain>("base");
  const [address, setAddress] = useState("0x0000000000000000000000000000000000000000");
  const [source, setSource] = useState(sampleSource);
  const [depth, setDepth] = useState<"preliminary" | "standard" | "deep">("preliminary");
  const [tier, setTier] = useState<Tier>("free");
  const [allowBytecodeOnly, setAllowBytecodeOnly] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedTier = window.localStorage.getItem("wr3-local-tier") as Tier | null;
    if (storedTier && ["free", "hobby", "team", "pro"].includes(storedTier)) {
      setTier(storedTier);
    }
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await createAudit({
        chain,
        address,
        source,
        allow_bytecode_only: allowBytecodeOnly,
        requested_depth: depth,
        visibility: "private",
        user_intent: "pre_launch_self_check",
        tier
      });
      router.push(`/audits/${response.audit_id}?owner_token=${encodeURIComponent(response.owner_access_token)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Скан не запустился");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="scan-console" onSubmit={submit}>
      <div className="scan-header">
        <div>
          <p className="eyebrow">Консоль wr3</p>
          <h1>ИИ-предаудит и триаж рисков смарт-контрактов</h1>
        </div>
        <div className="console-core-mark">
          <Cpu aria-hidden="true" size={27} />
          <ShieldAlert aria-hidden="true" size={18} />
        </div>
      </div>

      <div className="control-stack">
        <div>
          <div className="control-label">Сеть</div>
          <div className="segment-row" aria-label="Сеть">
            {chains.map((item) => (
              <button
                type="button"
                key={item.value}
                className={chain === item.value ? "segment-chip segment-chip-active" : "segment-chip"}
                onClick={() => setChain(item.value)}
              >
                {item.label}
                {item.note ? <span>{item.note}</span> : null}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="control-label">Глубина</div>
          <div className="segment-row" aria-label="Глубина">
            {depths.map((item) => (
              <button
                type="button"
                key={item.value}
                className={depth === item.value ? "segment-chip segment-chip-active" : "segment-chip"}
                onClick={() => setDepth(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <label>
          Локальный тариф
          <select
            value={tier}
            onChange={(event) => {
              const nextTier = event.target.value as Tier;
              setTier(nextTier);
              window.localStorage.setItem("wr3-local-tier", nextTier);
            }}
          >
            <option value="free">Бесплатный</option>
            <option value="hobby">Хобби</option>
            <option value="team">Команда</option>
            <option value="pro">Про</option>
          </select>
        </label>
      </div>

      <label>
        Адрес контракта
        <input value={address} onChange={(event) => setAddress(event.target.value)} placeholder="0x..." />
      </label>

      <label>
        Исходный код
        <textarea value={source} onChange={(event) => setSource(event.target.value)} rows={9} />
      </label>

      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={allowBytecodeOnly}
          onChange={(event) => setAllowBytecodeOnly(event.target.checked)}
        />
        <span>Разрешить ограниченный bytecode-скан, если верифицированный исходный код не найден</span>
      </label>

      <div className="scan-actions">
        <button type="button" className="secondary-button" onClick={() => setSource(sampleSource)}>
          <ClipboardPaste aria-hidden="true" size={17} />
          Демо-код
        </button>
        <button type="submit" disabled={isSubmitting || (!address && !source)}>
          {isSubmitting ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <ArrowRight aria-hidden="true" size={17} />}
          Запустить скан
        </button>
      </div>

      {error ? <p className="error-box">{error}</p> : null}
    </form>
  );
}
