import type { ScoreBreakdown } from "@wr3/shared";
import { tCap } from "@/lib/i18n";
import { RiskBadge } from "./RiskBadge";

const labels: Record<string, string> = {
  code_security_score: "Безопасность кода",
  centralization_score: "Централизация",
  liquidity_score: "Ликвидность",
  team_kyc_score: "Команда/KYC",
  behavior_score: "Поведение в сети"
};

export function ScorePanel({ score }: { score: ScoreBreakdown | null }) {
  if (!score) {
    return (
      <section className="panel score-panel">
        <div>
          <p className="eyebrow">Оценка риска</p>
          <h2>Ожидает расчёта</h2>
        </div>
        <RiskBadge score={null} />
      </section>
    );
  }

  const rows = [
    "code_security_score",
    "centralization_score",
    "liquidity_score",
    "team_kyc_score",
    "behavior_score"
  ] as const;

  return (
    <section className="panel score-panel">
      <div className="score-main">
        <p className="eyebrow">Оценка риска</p>
        <div className="score-number">{score.final_score}</div>
        <RiskBadge score={score.final_score} />
      </div>
      <div className="score-bars">
        {rows.map((key) => (
          <div className="score-row" key={key}>
            <div className="score-row-label">
              <span>{labels[key]}</span>
              <strong>{score[key]}</strong>
            </div>
            <div className="meter" aria-hidden="true">
              <span style={{ width: `${score[key]}%` }} />
            </div>
          </div>
        ))}
      </div>
      {score.caps_applied.length > 0 ? (
        <div className="caps">Ограничения оценки: {score.caps_applied.map(tCap).join(", ")}</div>
      ) : null}
    </section>
  );
}
