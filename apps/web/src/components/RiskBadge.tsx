import { AlertTriangle, CheckCircle2, CircleAlert, ShieldCheck } from "lucide-react";
import { scoreBand } from "@wr3/shared";

type RiskBadgeProps = {
  score: number | null;
};

export function RiskBadge({ score }: RiskBadgeProps) {
  if (score === null) {
    return <span className="risk-badge risk-badge-pending">Ожидает расчёта</span>;
  }

  const band = scoreBand(score);
  const Icon =
    band === "red" ? CircleAlert : band === "yellow" ? AlertTriangle : band === "green" ? CheckCircle2 : ShieldCheck;

  return (
    <span className={`risk-badge risk-badge-${band}`}>
      <Icon aria-hidden="true" size={16} />
      {band === "red" ? "Высокий риск" : band === "yellow" ? "Осторожно" : band === "green" ? "Приемлемо" : "Отлично"}
    </span>
  );
}
