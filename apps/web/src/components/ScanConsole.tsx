"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, ClipboardPaste, Loader2, ShieldAlert } from "lucide-react";
import type { Chain } from "@wr3/shared";
import { createAudit } from "@/lib/api";

const sampleSource = `contract Vault {
    address public owner;

    function auth(address expected) public view {
        require(tx.origin == expected, "bad auth");
    }
}`;

export function ScanConsole() {
  const router = useRouter();
  const [chain, setChain] = useState<Chain>("base");
  const [address, setAddress] = useState("0x0000000000000000000000000000000000000000");
  const [source, setSource] = useState(sampleSource);
  const [depth, setDepth] = useState<"preliminary" | "standard" | "deep">("preliminary");
  const [allowBytecodeOnly, setAllowBytecodeOnly] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        user_intent: "pre_launch_self_check"
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
          <p className="eyebrow">wr3 MVP</p>
          <h1>AI-предаудит и триаж рисков смарт-контрактов</h1>
        </div>
        <ShieldAlert aria-hidden="true" size={34} />
      </div>

      <div className="input-grid">
        <label>
          Сеть
          <select value={chain} onChange={(event) => setChain(event.target.value as Chain)}>
            <option value="ethereum">Ethereum</option>
            <option value="base">Base</option>
            <option value="bsc">BSC</option>
            <option value="arbitrum">Arbitrum</option>
            <option value="solana">Solana beta</option>
          </select>
        </label>
        <label>
          Глубина
          <select value={depth} onChange={(event) => setDepth(event.target.value as "preliminary" | "standard" | "deep")}>
            <option value="preliminary">Предварительная</option>
            <option value="standard">Стандартная</option>
            <option value="deep">Глубокая</option>
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
        <span>Разрешить bytecode-only limited scan, если verified source не найден</span>
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
