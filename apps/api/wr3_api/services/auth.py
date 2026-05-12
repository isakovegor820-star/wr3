from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import parse_qsl

from wr3_api.core.config import get_settings
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
    utc_now,
)


@dataclass(frozen=True)
class AuthContext:
    user_id: str | None = None
    provider: str | None = None
    subject: str | None = None
    is_reviewer: bool = False

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None


@dataclass(frozen=True)
class AuditAccessContext:
    actor: AuthContext
    owner_token: str | None = None
    public_token: str | None = None


@dataclass
class _Nonce:
    address: str
    nonce: str
    message: str
    expires_at: object


@dataclass
class _EmailMagicToken:
    email: str
    token: str
    expires_at: object


class AuthService:
    """Local MVP auth boundary.

    This intentionally does not pretend to be production auth. It gives the API
    a typed owner/reviewer/session boundary while SIWE signature verification
    and email delivery are wired later through NextAuth or wallet libraries.
    """

    def __init__(self) -> None:
        self._nonces: dict[str, _Nonce] = {}
        self._email_tokens: dict[str, _EmailMagicToken] = {}
        self._sessions: dict[str, AuthSessionResponse] = {}

    def create_siwe_nonce(self, request: SiweNonceRequest) -> SiweNonceResponse:
        nonce = secrets.token_urlsafe(18)
        expires_at = utc_now() + timedelta(minutes=10)
        message = (
            "wr3 AI pre-audit sign-in\n"
            f"Address: {request.address}\n"
            f"Chain: {request.chain}\n"
            f"Nonce: {nonce}\n"
            "Purpose: authenticate without authorizing transactions."
        )
        self._nonces[nonce] = _Nonce(
            address=request.address.lower(),
            nonce=nonce,
            message=message,
            expires_at=expires_at,
        )
        return SiweNonceResponse(nonce=nonce, message=message, expires_at=expires_at)

    def verify_siwe_stub(self, request: SiweVerifyRequest) -> AuthSessionResponse:
        nonce = self._nonces.get(request.nonce)
        if nonce is None:
            raise ValueError("unknown_or_expired_nonce")
        if nonce.address != request.address.lower() or nonce.message != request.message:
            raise ValueError("siwe_message_mismatch")
        if len(request.signature.strip()) < 8:
            raise ValueError("signature_required")
        settings = get_settings()
        limitations: list[str] = []
        if settings.siwe_signature_verification_enabled:
            self._verify_siwe_signature(request.message, request.signature, request.address)
            limitations.append("siwe_signature_verified")
        else:
            if len(request.signature.strip()) < 8:
                raise ValueError("signature_required")
            limitations.append("siwe_signature_verification_disabled_local_stub")
        del self._nonces[request.nonce]
        return self._create_session(
            provider="siwe",
            subject=request.address.lower(),
            limitations=limitations,
        )

    def request_email_magic_link_stub(self, request: EmailLoginRequest) -> AuthSessionResponse:
        return self._create_session(
            provider="email",
            subject=request.email,
            limitations=["email_delivery_stub_local_session_issued"],
        )

    def request_email_magic_link(self, request: EmailMagicLinkRequest) -> EmailMagicLinkResponse:
        settings = get_settings()
        token = secrets.token_urlsafe(32)
        expires_at = utc_now() + timedelta(minutes=15)
        self._email_tokens[token] = _EmailMagicToken(
            email=request.email,
            token=token,
            expires_at=expires_at,
        )
        base_url = settings.email_magic_link_base_url or f"{settings.web_base_url}/auth/email"
        magic_link_url = f"{base_url}?email={request.email}&token={token}"
        limitations = ["email_magic_link_token_expires_in_15_minutes"]
        if not settings.email_delivery_enabled:
            limitations.append("email_delivery_disabled_dev_token_returned")
        return EmailMagicLinkResponse(
            email=request.email,
            delivery_enabled=settings.email_delivery_enabled,
            magic_link_url=magic_link_url if settings.email_delivery_enabled else None,
            dev_verify_token=None if settings.email_delivery_enabled else token,
            expires_at=expires_at,
            limitations=limitations,
        )

    def verify_email_magic_link(self, request: EmailMagicLinkVerifyRequest) -> AuthSessionResponse:
        token = self._email_tokens.get(request.token)
        if token is None:
            raise ValueError("email_magic_link_unknown_or_used")
        if token.email != request.email:
            raise ValueError("email_magic_link_email_mismatch")
        if utc_now() > token.expires_at:
            del self._email_tokens[request.token]
            raise ValueError("email_magic_link_expired")
        del self._email_tokens[request.token]
        return self._create_session(
            provider="email",
            subject=request.email,
            limitations=["email_magic_link_verified"],
        )

    def verify_telegram_init_data(self, request: TelegramInitDataRequest) -> AuthSessionResponse:
        if not request.explicit_account_consent:
            raise ValueError("telegram_account_consent_required")
        settings = get_settings()
        if not settings.telegram_bot_token:
            raise ValueError("telegram_bot_token_not_configured")
        pairs = dict(parse_qsl(request.init_data, keep_blank_values=True))
        provided_hash = pairs.pop("hash", None)
        if not provided_hash:
            raise ValueError("telegram_init_data_hash_required")
        data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
        secret_key = hmac.new(
            b"WebAppData",
            settings.telegram_bot_token.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, provided_hash):
            raise ValueError("telegram_init_data_hash_mismatch")
        auth_date_raw = pairs.get("auth_date")
        if not auth_date_raw or not auth_date_raw.isdigit():
            raise ValueError("telegram_auth_date_required")
        age = utc_now().timestamp() - int(auth_date_raw)
        if age < 0 or age > settings.telegram_init_data_max_age_seconds:
            raise ValueError("telegram_init_data_expired")
        user_payload = pairs.get("user")
        if not user_payload:
            raise ValueError("telegram_user_required")
        try:
            user = json.loads(user_payload)
        except json.JSONDecodeError as exc:
            raise ValueError("telegram_user_invalid_json") from exc
        user_id = str(user.get("id") or "").strip()
        if not user_id:
            raise ValueError("telegram_user_id_required")
        return self._create_session(
            provider="telegram",
            subject=user_id,
            limitations=["telegram_init_data_verified", "telegram_account_created_with_explicit_consent"],
        )

    def context_from_headers(
        self,
        *,
        authorization: str | None = None,
        x_wr3_user: str | None = None,
        x_wr3_reviewer: str | None = None,
    ) -> AuthContext:
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            session = self._sessions.get(token)
            if session is not None:
                return AuthContext(
                    user_id=session.user_id,
                    provider=session.provider,
                    subject=session.subject,
                    is_reviewer=x_wr3_reviewer == "true",
                )
        if x_wr3_user:
            subject = x_wr3_user.strip()
            return AuthContext(
                user_id=f"dev:{subject}",
                provider="dev-header",
                subject=subject,
                is_reviewer=x_wr3_reviewer == "true",
            )
        return AuthContext(is_reviewer=x_wr3_reviewer == "true")

    def _create_session(
        self,
        *,
        provider: str,
        subject: str,
        limitations: list[str],
    ) -> AuthSessionResponse:
        token = secrets.token_urlsafe(32)
        session = AuthSessionResponse(
            user_id=f"{provider}:{subject}",
            provider=provider,
            subject=subject,
            bearer_token=token,
            expires_at=utc_now() + timedelta(days=7),
            limitations=limitations,
        )
        self._sessions[token] = session
        return session

    def _verify_siwe_signature(self, message: str, signature: str, address: str) -> None:
        try:
            from eth_account import Account
            from eth_account.messages import encode_defunct
        except ImportError as exc:
            raise ValueError("eth_account_required_for_siwe_verification") from exc
        recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
        if recovered.lower() != address.lower():
            raise ValueError("siwe_signature_address_mismatch")
