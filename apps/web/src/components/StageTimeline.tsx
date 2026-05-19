import type { AuditState } from "@wr3/shared";
import { Check, Clock, Minus, X } from "lucide-react";

const stages: { state: AuditState; label: string }[] = [
  { state: "ingesting", label: "Исходники" },
  { state: "static_running", label: "Статический анализ" },
  { state: "triage_running", label: "ИИ-триаж" },
  { state: "poc_running", label: "PoC" },
  { state: "fuzzing_running", label: "Фаззинг" },
  { state: "scoring", label: "Скоринг" },
  { state: "completed", label: "Отчёт" }
];

const order = stages.map((stage) => stage.state);

export function StageTimeline({
  state,
  failedStages,
  limitations,
  staticAnalysisStatus = "not_started"
}: {
  state: AuditState;
  failedStages: string[];
  limitations: string[];
  staticAnalysisStatus?: string;
}) {
  const currentIndex = order.indexOf(state);
  const isTerminalFailure = state === "failed" || state === "rejected";
  const skipsHeavyStages = limitations.some(
    (item) =>
      item.includes("poc_requires") ||
      item.includes("poc_no_high_or_critical_candidates") ||
      item.includes("foundry_binary_missing") ||
      item.includes("poc_generation_stub") ||
      item.includes("fuzzing_requires") ||
      item.includes("fuzzing_binaries_missing") ||
      item.includes("fuzzing_generation_stub")
  );

  return (
    <ol className="stage-grid" aria-label="Прогресс аудита">
      {stages.map((stage, index) => {
        const skipped = skipsHeavyStages && (stage.state === "poc_running" || stage.state === "fuzzing_running");
        const partial = stage.state === "static_running" && staticAnalysisStatus === "partial";
        const complete = state === "completed" || (currentIndex >= 0 && index < currentIndex);
        const active = stage.state === state || (state === "partial" && index >= 1);
        const failed =
          isTerminalFailure ||
          (stage.state === "static_running"
            ? staticAnalysisStatus === "failed"
            : failedStages.some((item) => item.includes(stage.state.split("_")[0])));
        const Icon = failed ? X : skipped || partial ? Minus : complete ? Check : Clock;
        return (
          <li
            key={stage.state}
            className={
              partial
                ? "stage stage-partial"
                : skipped
                  ? "stage stage-skipped"
                  : complete
                    ? "stage stage-complete"
                    : active
                      ? "stage stage-active"
                      : "stage"
            }
          >
            <span className={failed ? "stage-icon stage-icon-failed" : skipped || partial ? "stage-icon stage-icon-skipped" : "stage-icon"}>
              <Icon aria-hidden="true" size={15} />
            </span>
            <span>{partial ? `${stage.label}: частично` : skipped ? `${stage.label}: пропущено` : stage.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
