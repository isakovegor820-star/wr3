"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Loader2, Send } from "lucide-react";
import { telegramEmulatorCommand, type TelegramEmulatorResponse } from "@/lib/api";
import { tLimitation } from "@/lib/i18n";

const examples = [
  "/scan base 0x0000000000000000000000000000000000000000",
  "/watch base 0x0000000000000000000000000000000000000000 demo",
  "/score base 0x0000000000000000000000000000000000000000"
];

export function TelegramEmulator() {
  const [command, setCommand] = useState(examples[0]);
  const [response, setResponse] = useState<TelegramEmulatorResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      setResponse(await telegramEmulatorCommand(command));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Команда не выполнилась");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="panel emulator-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Локальный симулятор Telegram</p>
          <h2>Проверь /scan, /watch и /score без BotFather</h2>
        </div>
      </div>

      <div className="quick-command-grid">
        {examples.map((example) => (
          <button type="button" className="secondary-button" key={example} onClick={() => setCommand(example)}>
            {example}
          </button>
        ))}
      </div>

      <form className="telegram-form" onSubmit={submit}>
        <label>
          Команда
          <input value={command} onChange={(event) => setCommand(event.target.value)} />
        </label>
        <button type="submit" disabled={isSubmitting || command.trim().length === 0}>
          {isSubmitting ? <Loader2 className="spin" aria-hidden="true" size={17} /> : <Send aria-hidden="true" size={17} />}
          Отправить
        </button>
      </form>

      {error ? <p className="error-box">{error}</p> : null}
      {response ? (
        <div className="telegram-chat">
          <div className="telegram-bubble telegram-bubble-user">{command}</div>
          <div className="telegram-bubble telegram-bubble-bot">
            <p>{response.reply}</p>
            {response.status_url ? (
              <Link href={new URL(response.status_url).pathname + new URL(response.status_url).search}>
                Открыть отчёт аудита
              </Link>
            ) : null}
            {response.limitations?.length ? (
              <ul>
                {response.limitations.map((limitation) => (
                  <li key={limitation}>{tLimitation(limitation)}</li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      ) : (
        <p className="empty-state">Ответ Telegram-бота появится здесь.</p>
      )}
    </section>
  );
}
