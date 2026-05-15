"use client";

import { FormEvent, useEffect, useState } from "react";
import { FileLock2, Loader2, Plus, Send } from "lucide-react";
import {
  advanceDisclosureCase,
  appendDisclosureContact,
  createDisclosureCase,
  listDisclosureCases,
  type DisclosureCase
} from "@/lib/api";
import { tStatus } from "@/lib/i18n";

const timeline = [
  ["День 0", "приватный контакт"],
  ["День 7", "эскалация в SEAL 911"],
  ["День 14", "подготовка CVE/EUVD"],
  ["День 45", "координированное уведомление"],
  ["День 90", "ограниченное раскрытие"],
  ["День 180", "полный PoC только если разрешено"]
];

const statuses = [
  "private_contact_pending",
  "seal_911_escalation",
  "cve_euvd_notice",
  "limited_disclosure_allowed",
  "full_disclosure_allowed",
  "resolved",
  "closed"
];

export function DisclosureManager() {
  const [cases, setCases] = useState<DisclosureCase[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [findingId, setFindingId] = useState("wr3-find-local-demo");
  const [projectContact, setProjectContact] = useState("security@example.com");
  const [scopeNote, setScopeNote] = useState("Только пассивное раскрытие. Никаких активных действий в mainnet.");
  const [contactMessage, setContactMessage] = useState("Первичное приватное уведомление отправлено.");
  const [channel, setChannel] = useState("email");
  const [status, setStatus] = useState(statuses[0]);
  const [note, setNote] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const selected = cases.find((item) => item.id === selectedId) ?? cases[0] ?? null;

  async function load() {
    setError(null);
    setIsLoading(true);
    try {
      const nextCases = await listDisclosureCases();
      setCases(nextCases);
      setSelectedId((current) => current ?? nextCases[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Кейсы раскрытия не загрузились");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const created = await createDisclosureCase({
        finding_id: findingId,
        project_contact: projectContact,
        scope_note: scopeNote
      });
      await load();
      setSelectedId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Кейс не создан");
    }
  }

  async function submitContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setError(null);
    try {
      await appendDisclosureContact(selected.id, { channel, message: contactMessage });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Журнал контактов не сохранился");
    }
  }

  async function submitAdvance(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setError(null);
    try {
      await advanceDisclosureCase(selected.id, { status, note });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Переход статуса не сохранился");
    }
  }

  return (
    <section className="panel disclosure-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Ответственное раскрытие</p>
          <h2>Приватный локальный трекер кейсов</h2>
        </div>
        <div className="safe-harbor-signal">
          <FileLock2 aria-hidden="true" size={18} />
          <span>API только для ревьюера</span>
        </div>
      </div>

      {error ? <p className="error-box">{error}</p> : null}
      {isLoading ? <p className="empty-state">Загружаю кейсы раскрытия...</p> : null}

      <div className="disclosure-grid">
        <form className="stacked-form" onSubmit={submitCreate}>
          <h3>Создать кейс</h3>
          <label>
            ID находки
            <input value={findingId} onChange={(event) => setFindingId(event.target.value)} />
          </label>
          <label>
            Контакт проекта
            <input value={projectContact} onChange={(event) => setProjectContact(event.target.value)} />
          </label>
          <label>
            Заметка о scope
            <textarea rows={4} value={scopeNote} onChange={(event) => setScopeNote(event.target.value)} />
          </label>
          <button type="submit">
            <Plus aria-hidden="true" size={17} />
            Создать
          </button>
        </form>

        <div className="case-list">
          <h3>Кейсы</h3>
          {cases.length === 0 ? <p className="empty-state">Пока нет кейсов.</p> : null}
          {cases.map((item) => (
            <button
              type="button"
              className={`case-pill ${item.id === selected?.id ? "case-pill-active" : ""}`}
              key={item.id}
              onClick={() => {
                setSelectedId(item.id);
                setStatus(item.status);
              }}
            >
              <span>{item.finding_id}</span>
              <strong>{tStatus(item.status)}</strong>
            </button>
          ))}
        </div>
      </div>

      <div className="timeline-grid" aria-label="Таймлайн раскрытия">
        {timeline.map(([day, label]) => (
          <div className="timeline-step" key={day}>
            <strong>{day}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>

      {selected ? (
        <div className="disclosure-detail">
          <div>
            <p className="eyebrow">Детали кейса</p>
            <h3>{selected.id}</h3>
            <p className="muted-copy">
              {selected.finding_id} · {tStatus(selected.status)} · следующий срок {new Date(selected.deadline_next).toLocaleString()}
            </p>
            <ul className="contact-log">
              {selected.contact_log.map((entry) => (
                <li key={entry}>{entry}</li>
              ))}
            </ul>
          </div>
          <form className="stacked-form" onSubmit={submitContact}>
            <h3>Журнал контактов</h3>
            <label>
              Канал
              <input value={channel} onChange={(event) => setChannel(event.target.value)} />
            </label>
            <label>
              Сообщение
              <textarea rows={3} value={contactMessage} onChange={(event) => setContactMessage(event.target.value)} />
            </label>
            <button type="submit">
              <Send aria-hidden="true" size={17} />
              Добавить лог
            </button>
          </form>
          <form className="stacked-form" onSubmit={submitAdvance}>
            <h3>Переход статуса</h3>
            <label>
              Статус
              <select value={status} onChange={(event) => setStatus(event.target.value)}>
                {statuses.map((item) => (
                  <option value={item} key={item}>
                    {tStatus(item)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Заметка
              <input value={note} onChange={(event) => setNote(event.target.value)} />
            </label>
            <button type="submit">
              <Loader2 aria-hidden="true" size={17} />
              Обновить статус
            </button>
          </form>
        </div>
      ) : null}
    </section>
  );
}
