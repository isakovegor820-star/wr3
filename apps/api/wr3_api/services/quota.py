from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

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


TIER_POLICIES: dict[Tier, TierPolicy] = {
    Tier.FREE: TierPolicy(
        scan_quota=1,
        window=timedelta(hours=24),
        max_depth=RequestedDepth.PRELIMINARY,
        poc_allowed=False,
        retention_days=7,
    ),
    Tier.HOBBY: TierPolicy(
        scan_quota=10,
        window=timedelta(days=30),
        max_depth=RequestedDepth.STANDARD,
        poc_allowed=False,
        retention_days=30,
    ),
    Tier.TEAM: TierPolicy(
        scan_quota=100,
        window=timedelta(days=30),
        max_depth=RequestedDepth.DEEP,
        poc_allowed=True,
        retention_days=180,
    ),
    Tier.PRO: TierPolicy(
        scan_quota=None,
        window=None,
        max_depth=RequestedDepth.DEEP,
        poc_allowed=True,
        retention_days=365,
    ),
}


class InMemoryQuotaLimiter:
    """MVP quota and tier policy.

    This intentionally stores only non-sensitive counters. Production should move
    this to Redis/Postgres with user + IP + address tuple rate limits.
    """

    def __init__(self) -> None:
        self._windows: dict[tuple[str, Tier], tuple[datetime, int]] = {}

    def check(
        self,
        *,
        user_key: str,
        tier: Tier,
        requested_depth: RequestedDepth,
    ) -> QuotaDecision:
        policy = TIER_POLICIES[tier]
        limitations: list[str] = []
        effective_depth = requested_depth

        if DEPTH_ORDER[requested_depth] > DEPTH_ORDER[policy.max_depth]:
            effective_depth = policy.max_depth
            limitations.append(f"{tier}_max_depth_{policy.max_depth}_applied")

        if tier != Tier.FREE:
            limitations.append(f"{tier}_billing_verification_stub")

        if policy.scan_quota is None or policy.window is None:
            return QuotaDecision(
                allowed=True,
                effective_depth=effective_depth,
                poc_allowed=policy.poc_allowed,
                retention_days=policy.retention_days,
                limitations=limitations,
            )

        now = datetime.now(UTC)
        key = (user_key, tier)
        window_start, count = self._windows.get(key, (now, 0))
        if now - window_start > policy.window:
            window_start, count = now, 0

        count += 1
        self._windows[key] = (window_start, count)
        if count > policy.scan_quota:
            effective_depth = RequestedDepth.PRELIMINARY
            limitations.append(f"{tier}_quota_degraded_mode_static_only_after_window_quota")
            return QuotaDecision(
                allowed=True,
                effective_depth=effective_depth,
                poc_allowed=False,
                retention_days=policy.retention_days,
                limitations=limitations,
            )
        return QuotaDecision(
            allowed=True,
            effective_depth=effective_depth,
            poc_allowed=policy.poc_allowed,
            retention_days=policy.retention_days,
            limitations=limitations,
        )
