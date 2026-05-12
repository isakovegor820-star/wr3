from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from wr3_api.api.dependencies import get_optional_auth
from wr3_api.domain.schemas import CheckoutIntentRequest, ConfirmSubscriptionRequest, ManualPaymentIntentRequest
from wr3_api.services.auth import AuthContext
from wr3_api.services.billing import BillingAccessDenied, BillingService

router = APIRouter(prefix="/v1/billing", tags=["billing"])
service = BillingService()


@router.get("/plans")
async def list_plans():
    return service.list_plans()


@router.get("/one-shot-packages")
async def list_one_shot_packages():
    return service.list_one_shot_packages()


@router.post("/manual-usdc-intents")
async def create_manual_usdc_intent(
    request: ManualPaymentIntentRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.create_manual_payment_intent(request, actor)
    except BillingAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/checkout-intents")
async def create_checkout_intent(
    request: CheckoutIntentRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.create_checkout_intent(request, actor)
    except BillingAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/subscription")
async def get_subscription(actor: AuthContext = Depends(get_optional_auth)):
    try:
        subscription = service.get_subscription(actor)
    except BillingAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return subscription or {"status": "none", "tier": "free"}


@router.post("/subscriptions/confirm-manual")
async def confirm_manual_subscription(
    request: ConfirmSubscriptionRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.confirm_subscription(request, actor)
    except BillingAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
