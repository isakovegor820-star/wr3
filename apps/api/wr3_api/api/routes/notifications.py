from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from wr3_api.api.dependencies import get_optional_auth
from wr3_api.domain.schemas import WatchlistRequest, WebhookTestRequest
from wr3_api.services.auth import AuthContext
from wr3_api.services.notifications import NotificationAccessDenied, NotificationService

router = APIRouter(prefix="/v1", tags=["notifications"])
service = NotificationService()


@router.post("/watchlist")
async def add_watchlist_entry(
    request: WatchlistRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.add_watchlist_entry(request, actor)
    except NotificationAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/webhooks/test")
async def test_webhook(
    request: WebhookTestRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return await service.test_webhook(request, actor)
    except NotificationAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
