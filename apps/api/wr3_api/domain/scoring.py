from dataclasses import dataclass

from wr3_api.domain.enums import Exploitability, Severity
from wr3_api.domain.schemas import Finding, ScoreBreakdown, ScoreWeights

SCORE_VERSION = "wr3-score-v0.1"
SCORE_WEIGHTS = ScoreWeights(
    code_security=0.35,
    centralization=0.20,
    liquidity=0.15,
    team_kyc=0.15,
    behavior=0.15,
)

SEVERITY_PENALTY = {
    Severity.CRITICAL: 45,
    Severity.HIGH: 25,
    Severity.MEDIUM: 10,
    Severity.LOW: 3,
    Severity.INFO: 0,
}

EXPLOITABILITY_MULTIPLIER = {
    Exploitability.CONFIRMED: 1.0,
    Exploitability.LIKELY: 0.75,
    Exploitability.THEORETICAL: 0.45,
    Exploitability.UNKNOWN: 0.25,
    Exploitability.DISMISSED: 0.0,
}


@dataclass(frozen=True)
class ScoreContext:
    unverified_source: bool = False
    upgradeable_proxy_with_eoa_owner: bool = False
    unlimited_owner_mint: bool = False
    safe_harbor_and_bounty: bool = False
    centralization_score: int = 85
    liquidity_score: int = 80
    team_kyc_score: int = 70
    behavior_score: int = 80


def _clamp_score(value: float) -> int:
    return max(0, min(100, round(value)))


def _finding_penalty(finding: Finding) -> float:
    base = SEVERITY_PENALTY[finding.severity]
    if finding.severity in {Severity.LOW, Severity.INFO}:
        return base * finding.confidence
    return base * finding.confidence * EXPLOITABILITY_MULTIPLIER[finding.exploitability]


def score_audit(findings: list[Finding], context: ScoreContext | None = None) -> ScoreBreakdown:
    ctx = context or ScoreContext()
    active = [finding for finding in findings if finding.exploitability != Exploitability.DISMISSED]
    code_security_score = _clamp_score(100 - sum(_finding_penalty(finding) for finding in active))

    final_score = (
        SCORE_WEIGHTS.code_security * code_security_score
        + SCORE_WEIGHTS.centralization * ctx.centralization_score
        + SCORE_WEIGHTS.liquidity * ctx.liquidity_score
        + SCORE_WEIGHTS.team_kyc * ctx.team_kyc_score
        + SCORE_WEIGHTS.behavior * ctx.behavior_score
    )
    if ctx.safe_harbor_and_bounty:
        final_score += 5

    caps_applied: list[str] = []

    def apply_cap(cap: int, reason: str) -> None:
        nonlocal final_score
        if final_score > cap:
            final_score = cap
            caps_applied.append(reason)

    if any(
        finding.severity == Severity.CRITICAL and finding.exploitability == Exploitability.CONFIRMED
        for finding in active
    ):
        apply_cap(39, "confirmed_critical")
    if any(
        finding.severity == Severity.HIGH and finding.exploitability == Exploitability.CONFIRMED
        for finding in active
    ):
        apply_cap(69, "confirmed_high")
    if ctx.unverified_source:
        apply_cap(79, "unverified_source")
    if ctx.upgradeable_proxy_with_eoa_owner:
        apply_cap(69, "upgradeable_proxy_eoa_owner")
    if ctx.unlimited_owner_mint:
        apply_cap(59, "unlimited_owner_mint")

    return ScoreBreakdown(
        score_version=SCORE_VERSION,
        final_score=_clamp_score(final_score),
        code_security_score=code_security_score,
        centralization_score=_clamp_score(ctx.centralization_score),
        liquidity_score=_clamp_score(ctx.liquidity_score),
        team_kyc_score=_clamp_score(ctx.team_kyc_score),
        behavior_score=_clamp_score(ctx.behavior_score),
        caps_applied=caps_applied,
        weights=SCORE_WEIGHTS,
    )
