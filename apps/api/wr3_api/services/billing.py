from __future__ import annotations

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Tier
from wr3_api.domain.schemas import (
    BillingPlan,
    CheckoutIntent,
    CheckoutIntentRequest,
    ConfirmSubscriptionRequest,
    ManualPaymentIntent,
    ManualPaymentIntentRequest,
    OneShotAuditPackage,
    SubscriptionRecord,
)
from wr3_api.services.auth import AuthContext


PLANS: dict[Tier, BillingPlan] = {
    Tier.FREE: BillingPlan(
        tier=Tier.FREE,
        name="Free",
        price_usd_month=0,
        scan_quota="1 scan / 24h",
        retention_days=7,
        poc_access=False,
        notes=["Preliminary score only", "Static and triage degraded mode after quota"],
    ),
    Tier.HOBBY: BillingPlan(
        tier=Tier.HOBBY,
        name="Hobby",
        price_usd_month=29,
        scan_quota="10 scans / month",
        retention_days=30,
        poc_access=False,
        notes=["Mid-detail reports", "Telegram alerts planned"],
    ),
    Tier.TEAM: BillingPlan(
        tier=Tier.TEAM,
        name="Team",
        price_usd_month=99,
        scan_quota="100 scans / month fair-use",
        retention_days=180,
        poc_access=True,
        notes=["Foundry PoC worker access", "Human review gate for High/Critical"],
    ),
    Tier.PRO: BillingPlan(
        tier=Tier.PRO,
        name="Pro",
        price_usd_month=499,
        scan_quota="Custom",
        retention_days=365,
        poc_access=True,
        notes=["Monitoring/custom invariants planned", "Safe Harbor onboarding helper planned"],
    ),
}

ONE_SHOT_PACKAGES: tuple[OneShotAuditPackage, ...] = (
    OneShotAuditPackage(
        id="pre_launch_quickcheck",
        name="Pre-launch quickcheck",
        price_usd_min=200,
        price_usd_max=300,
        sla_hours_min=24,
        sla_hours_max=24,
        includes=["Static analysis", "LLM triage", "Risk score", "30-minute human pass"],
        limitations=["No warranty", "No active mainnet actions", "Private report by default"],
    ),
    OneShotAuditPackage(
        id="poc_report",
        name="PoC report",
        price_usd_min=500,
        price_usd_max=900,
        sla_hours_min=48,
        sla_hours_max=72,
        includes=["Quickcheck", "Foundry PoC attempts for top findings", "Mitigation notes"],
        limitations=["PoC artifacts gated to authorized owner", "Safe Harbor/explicit scope required for active validation"],
    ),
    OneShotAuditPackage(
        id="deep_ai_assisted_audit",
        name="Deep AI-assisted audit",
        price_usd_min=1200,
        price_usd_max=2000,
        sla_hours_min=120,
        sla_hours_max=168,
        includes=["PoC attempts", "AI-fuzzing/invariants", "Manual review", "Mitigation call"],
        limitations=["Not a replacement for full formal assurance", "Requires engagement scope before work starts"],
    ),
)


class BillingAccessDenied(PermissionError):
    pass


class BillingService:
    def __init__(self) -> None:
        self._checkout_intents: dict[str, CheckoutIntent] = {}
        self._intents: dict[str, ManualPaymentIntent] = {}
        self._subscriptions: dict[str, SubscriptionRecord] = {}

    def list_plans(self) -> list[BillingPlan]:
        return list(PLANS.values())

    def list_one_shot_packages(self) -> list[OneShotAuditPackage]:
        return list(ONE_SHOT_PACKAGES)

    def create_manual_payment_intent(
        self,
        request: ManualPaymentIntentRequest,
        actor: AuthContext,
    ) -> ManualPaymentIntent:
        if not actor.is_authenticated or actor.user_id is None:
            raise BillingAccessDenied("authenticated_user_required_for_payment_intent")
        plan = PLANS[request.tier]
        settings = get_settings()
        address = settings.usdc_receive_address or "configure_WR3_USDC_RECEIVE_ADDRESS"
        intent = ManualPaymentIntent(
            user_id=actor.user_id,
            tier=request.tier,
            amount_usd=plan.price_usd_month,
            payment_address=address,
            memo=f"wr3 {request.tier} subscription for {actor.user_id}",
            limitations=[
                "manual_usdc_confirmation_required",
                "request_finance_or_polar_integration_pending",
            ],
        )
        if settings.usdc_receive_address is None:
            intent.limitations.append("usdc_receive_address_not_configured")
        self._intents[intent.id] = intent
        return intent

    def create_checkout_intent(
        self,
        request: CheckoutIntentRequest,
        actor: AuthContext,
    ) -> CheckoutIntent:
        if not actor.is_authenticated or actor.user_id is None:
            raise BillingAccessDenied("authenticated_user_required_for_checkout_intent")
        plan = PLANS[request.tier]
        settings = get_settings()
        base_url = {
            "polar": settings.polar_checkout_base_url,
            "request_finance": settings.request_finance_invoice_base_url,
        }[request.provider]
        limitations = [
            "refund_policy_applies_only_to_undelivered_or_empty_reports",
            "paid_audit_requires_engagement_scope_before_active_validation",
        ]
        checkout_url = None
        status = "requires_provider_configuration"
        if base_url:
            checkout_url = self._build_checkout_url(base_url, actor.user_id, request.tier)
            status = "pending_provider_checkout"
        else:
            limitations.append(f"{request.provider}_checkout_url_not_configured")
        intent = CheckoutIntent(
            user_id=actor.user_id,
            tier=request.tier,
            amount_usd=plan.price_usd_month,
            provider=request.provider,
            checkout_url=checkout_url,
            status=status,
            limitations=limitations,
        )
        self._checkout_intents[intent.id] = intent
        return intent

    def get_subscription(self, actor: AuthContext) -> SubscriptionRecord | None:
        if not actor.is_authenticated or actor.user_id is None:
            raise BillingAccessDenied("authenticated_user_required_for_subscription")
        return self._subscriptions.get(actor.user_id)

    def confirm_subscription(
        self,
        request: ConfirmSubscriptionRequest,
        actor: AuthContext,
    ) -> SubscriptionRecord:
        if not actor.is_reviewer:
            raise BillingAccessDenied("reviewer_access_required_for_manual_subscription_confirmation")
        subscription = SubscriptionRecord(
            user_id=request.user_id,
            tier=request.tier,
            provider=request.provider,
            tx_reference=request.tx_reference,
        )
        self._subscriptions[request.user_id] = subscription
        return subscription

    def _build_checkout_url(self, base_url: str, user_id: str, tier: Tier) -> str:
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}client_reference_id={user_id}&tier={tier}"
