import type { Exploitability, Finding, Severity, ScoreBreakdown } from "./schemas.js";

export const SCORE_VERSION = "wr3-score-v0.1";

export const SCORE_WEIGHTS = {
  code_security: 0.35,
  centralization: 0.2,
  liquidity: 0.15,
  team_kyc: 0.15,
  behavior: 0.15
} as const;

const severityPenalty: Record<Severity, number> = {
  critical: 45,
  high: 25,
  medium: 10,
  low: 3,
  info: 0
};

const exploitabilityMultiplier: Record<Exploitability, number> = {
  confirmed: 1,
  likely: 0.75,
  theoretical: 0.45,
  unknown: 0.25,
  dismissed: 0
};

export type ScoreContext = {
  unverifiedSource?: boolean;
  upgradeableProxyWithEoaOwner?: boolean;
  unlimitedOwnerMint?: boolean;
  safeHarborAndBounty?: boolean;
  centralizationScore?: number;
  liquidityScore?: number;
  teamKycScore?: number;
  behaviorScore?: number;
};

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function findingPenalty(finding: Finding): number {
  const base = severityPenalty[finding.severity];
  if (finding.severity === "low" || finding.severity === "info") {
    return base * finding.confidence;
  }
  return base * finding.confidence * exploitabilityMultiplier[finding.exploitability];
}

export function scoreAudit(findings: Finding[], context: ScoreContext = {}): ScoreBreakdown {
  const activeFindings = findings.filter((finding) => finding.exploitability !== "dismissed");
  const penalty = activeFindings.reduce((sum, finding) => sum + findingPenalty(finding), 0);
  const codeSecurityScore = clampScore(100 - penalty);

  const centralizationScore = context.centralizationScore ?? 85;
  const liquidityScore = context.liquidityScore ?? 80;
  const teamKycScore = context.teamKycScore ?? 70;
  const behaviorScore = context.behaviorScore ?? 80;

  let finalScore =
    SCORE_WEIGHTS.code_security * codeSecurityScore +
    SCORE_WEIGHTS.centralization * centralizationScore +
    SCORE_WEIGHTS.liquidity * liquidityScore +
    SCORE_WEIGHTS.team_kyc * teamKycScore +
    SCORE_WEIGHTS.behavior * behaviorScore;

  if (context.safeHarborAndBounty) {
    finalScore += 5;
  }

  const capsApplied: string[] = [];
  const applyCap = (cap: number, reason: string) => {
    if (finalScore > cap) {
      capsApplied.push(reason);
      finalScore = cap;
    }
  };

  if (activeFindings.some((finding) => finding.severity === "critical" && finding.exploitability === "confirmed")) {
    applyCap(39, "confirmed_critical");
  }
  if (activeFindings.some((finding) => finding.severity === "high" && finding.exploitability === "confirmed")) {
    applyCap(69, "confirmed_high");
  }
  if (context.unverifiedSource) {
    applyCap(79, "unverified_source");
  }
  if (context.upgradeableProxyWithEoaOwner) {
    applyCap(69, "upgradeable_proxy_eoa_owner");
  }
  if (context.unlimitedOwnerMint) {
    applyCap(59, "unlimited_owner_mint");
  }

  return {
    score_version: SCORE_VERSION,
    final_score: clampScore(finalScore),
    code_security_score: codeSecurityScore,
    centralization_score: clampScore(centralizationScore),
    liquidity_score: clampScore(liquidityScore),
    team_kyc_score: clampScore(teamKycScore),
    behavior_score: clampScore(behaviorScore),
    caps_applied: capsApplied,
    weights: SCORE_WEIGHTS
  };
}

export function scoreBand(score: number): "red" | "yellow" | "green" | "blue" {
  if (score < 40) return "red";
  if (score < 70) return "yellow";
  if (score < 90) return "green";
  return "blue";
}
