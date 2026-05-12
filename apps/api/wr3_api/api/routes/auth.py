from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wr3_api.api.dependencies import auth_service
from wr3_api.domain.schemas import (
    AuthSessionResponse,
    EmailMagicLinkRequest,
    EmailMagicLinkResponse,
    EmailMagicLinkVerifyRequest,
    EmailLoginRequest,
    SiweNonceRequest,
    SiweNonceResponse,
    SiweVerifyRequest,
    TelegramInitDataRequest,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/siwe/nonce", response_model=SiweNonceResponse)
async def siwe_nonce(request: SiweNonceRequest) -> SiweNonceResponse:
    return auth_service.create_siwe_nonce(request)


@router.post("/siwe/verify", response_model=AuthSessionResponse)
async def siwe_verify(request: SiweVerifyRequest) -> AuthSessionResponse:
    try:
        return auth_service.verify_siwe_stub(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/email/request-link", response_model=AuthSessionResponse)
async def email_request_link(request: EmailLoginRequest) -> AuthSessionResponse:
    return auth_service.request_email_magic_link_stub(request)


@router.post("/email/magic-link", response_model=EmailMagicLinkResponse)
async def email_magic_link(request: EmailMagicLinkRequest) -> EmailMagicLinkResponse:
    return auth_service.request_email_magic_link(request)


@router.post("/email/verify-link", response_model=AuthSessionResponse)
async def email_verify_link(request: EmailMagicLinkVerifyRequest) -> AuthSessionResponse:
    try:
        return auth_service.verify_email_magic_link(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/telegram/init-data", response_model=AuthSessionResponse)
async def telegram_init_data(request: TelegramInitDataRequest) -> AuthSessionResponse:
    try:
        return auth_service.verify_telegram_init_data(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
