import type { Finding } from "@wr3/shared";
import { LockKeyhole, MapPin } from "lucide-react";
import { exploitabilityLabels, severityLabels, tFindingText } from "@/lib/i18n";

const severityOrder = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4
};

export function FindingsList({ findings }: { findings: Finding[] }) {
  const sorted = [...findings].sort(
    (left, right) => severityOrder[left.severity] - severityOrder[right.severity] || right.confidence - left.confidence
  );

  if (sorted.length === 0) {
    return <p className="empty-state">Для этого аудита находки пока недоступны.</p>;
  }

  return (
    <div className="findings-list">
      {sorted.map((finding) => (
        <article className="finding" key={finding.id}>
          <header className="finding-header">
            <span className={`severity severity-${finding.severity}`}>{severityLabels[finding.severity]}</span>
            <h3>{tFindingText(finding.summary)}</h3>
          </header>
          <div className="finding-meta">
            <span>
              <MapPin aria-hidden="true" size={14} />
              {finding.contract.file ?? "исходник"} {finding.location.start_line ? `:${finding.location.start_line}` : ""}
            </span>
            <span>уверенность {Math.round(finding.confidence * 100)}%</span>
            <span>{exploitabilityLabels[finding.exploitability]}</span>
          </div>
          <p>{tFindingText(finding.impact)}</p>
          <p className="recommendation">{tFindingText(finding.recommendation)}</p>
          {finding.evidence.poc_artifact_uri ? (
            <a className="artifact-link" href={finding.evidence.poc_artifact_uri}>
              PoC-артефакт
            </a>
          ) : (
            <span className="artifact-locked">
              <LockKeyhole aria-hidden="true" size={14} />
              PoC закрыт доступом или не запускался
            </span>
          )}
        </article>
      ))}
    </div>
  );
}
