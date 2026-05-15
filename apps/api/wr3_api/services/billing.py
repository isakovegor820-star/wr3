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
        name="Бесплатный",
        price_usd_month=0,
        scan_quota="1 скан / 24ч",
        retention_days=7,
        poc_access=False,
        notes=["Только предварительная оценка", "После квоты статический анализ и триаж идут в ограниченном режиме"],
    ),
    Tier.HOBBY: BillingPlan(
        tier=Tier.HOBBY,
        name="Хобби",
        price_usd_month=29,
        scan_quota="10 сканов / месяц",
        retention_days=30,
        poc_access=False,
        notes=["Отчёты средней детализации", "Telegram-алерты запланированы"],
    ),
    Tier.TEAM: BillingPlan(
        tier=Tier.TEAM,
        name="Команда",
        price_usd_month=99,
        scan_quota="100 сканов / месяц по честному использованию",
        retention_days=180,
        poc_access=True,
        notes=["Доступ к Foundry PoC worker", "Ручное ревью для высокой/критичной важности"],
    ),
    Tier.PRO: BillingPlan(
        tier=Tier.PRO,
        name="Про",
        price_usd_month=499,
        scan_quota="Индивидуально",
        retention_days=365,
        poc_access=True,
        notes=["Мониторинг и custom invariants запланированы", "Safe Harbor onboarding helper запланирован"],
    ),
}

ONE_SHOT_PACKAGES: tuple[OneShotAuditPackage, ...] = (
    OneShotAuditPackage(
        id="pre_launch_quickcheck",
        name="Быстрая проверка перед запуском",
        price_usd_min=200,
        price_usd_max=300,
        sla_hours_min=24,
        sla_hours_max=24,
        includes=["Статический анализ", "ИИ-триаж", "Оценка риска", "30-минутная ручная проверка"],
        limitations=["Без гарантии", "Без активных действий в mainnet", "Приватный отчёт по умолчанию"],
    ),
    OneShotAuditPackage(
        id="poc_report",
        name="Отчёт с PoC",
        price_usd_min=500,
        price_usd_max=900,
        sla_hours_min=48,
        sla_hours_max=72,
        includes=["Быстрая проверка", "Foundry PoC-попытки для главных находок", "Заметки по исправлению"],
        limitations=["PoC-артефакты закрыты для авторизованного владельца", "Для активной валидации нужен Safe Harbor или явный scope"],
    ),
    OneShotAuditPackage(
        id="deep_ai_assisted_audit",
        name="Глубокий аудит с ИИ",
        price_usd_min=1200,
        price_usd_max=2000,
        sla_hours_min=120,
        sla_hours_max=168,
        includes=["PoC-попытки", "ИИ-фаззинг/invariants", "Ручное ревью", "Созвон по исправлению"],
        limitations=["Не заменяет полноценную formal assurance", "До начала работы нужен согласованный scope"],
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
            memo=f"wr3 подписка {request.tier} для {actor.user_id}",
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
