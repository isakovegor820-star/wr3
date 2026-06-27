from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from wr3_api.domain.enums import RequestedDepth, Tier


DEPTH_ORDER: dict[RequestedDepth, int] = {
    RequestedDepth.PRELIMINARY: 0,
    RequestedDepth.STANDARD: 1,
    RequestedDepth.DEEP: 2,
}


@dataclass(frozen=True)
class TierPolicy:
    scan_quota: int | None
    window: timedelta | None
    max_depth: RequestedDepth
    poc_allowed: bool
    retention_days: int


@dataclass
class QuotaDecision:
    allowed: bool
    effective_depth: RequestedDepth
    poc_allowed: bool
    retention_days: int
    limitations: list[str] = field(default_factory=list)


UNRESTRICTED_POLICY = TierPolicy(
    scan_quota=None,
    window=None,
    max_depth=RequestedDepth.DEEP,
    poc_allowed=True,
    retention_days=365,
)

TIER_POLICIES: dict[Tier, TierPolicy] = {tier: UNRESTRICTED_POLICY for tier in Tier}


class InMemoryQuotaLimiter:
    """Compatibility boundary for old tiered requests.

    wr3 now runs in unrestricted local mode: no product tier reduces depth,
    PoC access, fuzzing, or retention. The tier argument remains accepted so
    older clients do not break while the UI removes access selectors completely.
    """

    def check(
        self,
        *,
        user_key: str,
        tier: Tier,
        requested_depth: RequestedDepth,
    ) -> QuotaDecision:
        policy = TIER_POLICIES[tier]
        return QuotaDecision(
            allowed=True,
            effective_depth=requested_depth,
            poc_allowed=policy.poc_allowed,
            retention_days=policy.retention_days,
            limitations=[],
        )
