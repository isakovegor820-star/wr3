import type { Finding } from "@wr3/shared";
import { CheckCircle2, LockKeyhole, MapPin, ShieldAlert } from "lucide-react";
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
              {finding.disclosure_assessment.location_label}
            </span>
            <span>уверенность {Math.round(finding.confidence * 100)}%</span>
            <span>{exploitabilityLabels[finding.exploitability]}</span>
          </div>
          <div className={`finding-verdict finding-verdict-${finding.disclosure_assessment.verdict}`}>
            {finding.disclosure_assessment.can_contact_support ? (
              <CheckCircle2 aria-hidden="true" size={16} />
            ) : (
              <ShieldAlert aria-hidden="true" size={16} />
            )}
            <div>
              <strong>{finding.disclosure_assessment.verdict_label}</strong>
              <span>{finding.disclosure_assessment.next_step}</span>
            </div>
          </div>
          <p>{finding.disclosure_assessment.plain_explanation}</p>
          <details className="finding-technical-details">
            <summary>Технические детали и ручная проверка</summary>
            <p>{finding.disclosure_assessment.technical_explanation}</p>
            {finding.disclosure_assessment.manual_checklist.length ? (
              <ul>
                {finding.disclosure_assessment.manual_checklist.map((item) => <li key={item}>{item}</li>)}
              </ul>
            ) : null}
            {finding.disclosure_assessment.evidence_gaps.length ? (
              <>
                <strong>Чего не хватает для письма</strong>
                <ul>
                  {finding.disclosure_assessment.evidence_gaps.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </>
            ) : null}
          </details>
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
