from wr3_api.domain.enums import RequestedDepth, Tier
from wr3_api.services.quota import InMemoryQuotaLimiter, TIER_POLICIES


def test_old_free_tier_request_still_gets_full_depth_without_quota():
    limiter = InMemoryQuotaLimiter()

    first = limiter.check(user_key="free-user", tier=Tier.FREE, requested_depth=RequestedDepth.PRELIMINARY)
    second = limiter.check(user_key="free-user", tier=Tier.FREE, requested_depth=RequestedDepth.DEEP)

    assert first.allowed is True
    assert first.effective_depth == RequestedDepth.PRELIMINARY
    assert second.allowed is True
    assert second.effective_depth == RequestedDepth.DEEP
    assert second.poc_allowed is True
    assert second.limitations == []


def test_old_hobby_tier_request_does_not_cap_depth_or_poc():
    limiter = InMemoryQuotaLimiter()

    decision = limiter.check(user_key="hobby-user", tier=Tier.HOBBY, requested_depth=RequestedDepth.DEEP)

    assert decision.effective_depth == RequestedDepth.DEEP
    assert decision.poc_allowed is True
    assert decision.limitations == []


def test_all_legacy_tiers_share_unrestricted_retention_policy():
    limiter = InMemoryQuotaLimiter()

    decision = limiter.check(user_key="team-user", tier=Tier.TEAM, requested_depth=RequestedDepth.DEEP)

    assert decision.effective_depth == RequestedDepth.DEEP
    assert decision.poc_allowed is True
    assert decision.retention_days == TIER_POLICIES[Tier.TEAM].retention_days
    assert TIER_POLICIES[Tier.FREE].retention_days == TIER_POLICIES[Tier.PRO].retention_days
