from wr3_api.domain.enums import RequestedDepth, Tier
from wr3_api.services.quota import InMemoryQuotaLimiter, TIER_POLICIES


def test_free_tier_degrades_after_daily_quota():
    limiter = InMemoryQuotaLimiter()

    first = limiter.check(user_key="free-user", tier=Tier.FREE, requested_depth=RequestedDepth.PRELIMINARY)
    second = limiter.check(user_key="free-user", tier=Tier.FREE, requested_depth=RequestedDepth.DEEP)

    assert first.allowed is True
    assert first.effective_depth == RequestedDepth.PRELIMINARY
    assert second.allowed is True
    assert second.effective_depth == RequestedDepth.PRELIMINARY
    assert "free_quota_degraded_mode_static_only_after_window_quota" in second.limitations


def test_hobby_tier_caps_depth_and_disables_poc():
    limiter = InMemoryQuotaLimiter()

    decision = limiter.check(user_key="hobby-user", tier=Tier.HOBBY, requested_depth=RequestedDepth.DEEP)

    assert decision.effective_depth == RequestedDepth.STANDARD
    assert decision.poc_allowed is False
    assert "hobby_max_depth_standard_applied" in decision.limitations
    assert "hobby_billing_verification_stub" in decision.limitations


def test_team_policy_allows_deep_and_poc_with_retention():
    limiter = InMemoryQuotaLimiter()

    decision = limiter.check(user_key="team-user", tier=Tier.TEAM, requested_depth=RequestedDepth.DEEP)

    assert decision.effective_depth == RequestedDepth.DEEP
    assert decision.poc_allowed is True
    assert decision.retention_days == TIER_POLICIES[Tier.TEAM].retention_days
